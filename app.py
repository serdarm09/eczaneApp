from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import datetime
import urllib3
import re
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
# github.com/serdarm09
# Disable SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def fetch_pharmacies(city_code, target_date=None):
    # E-Devlet'in nöbetçi eczane sorgulama adresi
    url = 'https://www.turkiye.gov.tr/saglik-titck-nobetci-eczane-sorgulama'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    # Bu kısım, tarayıcının e-Devlet'e "Ben bir Chrome kullanıcısıyım" demesini sağlar.
    # Bunlar olmadan e-Devlet sayfayı size göstermeyebilir (403 Forbidden hatası verebilir).
    session = requests.Session()
    
    # 1. GET Request to get the token and cookies
    try:
        response = session.get(url, headers=headers, verify=False)
        response.raise_for_status() # Eğer site çöktüyse hata fırlat
    except Exception as e:
        return {"error": f"E-Devlet'e bağlanılamadı: {str(e)}"}

    # Gelen HTML sayfasını BeautifulSoup kütüphanesi ile parçalıyoruz (parse ediyoruz)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Sayfa içindeki <input name="token"> etiketini buluyoruz
    token_input = soup.find('input', {'name': 'token'})
    if not token_input:
        return {"error": "Sayfada güvenlik token'ı bulunamadı."}
    
    # Token'ın değerini alıyoruz bir user gibi görünsün diye
    token = token_input.get('value')
    
    # Eğer tarih gönderilmemişse "bugünün" tarihini formatlayıp alıyoruz 
    if not target_date:
        target_date = datetime.datetime.now().strftime('%d/%m/%Y')

    # 2. ADIM: POST İsteği için verilerimizi hazırlıyoruz (Sanki "Sorgula" butonuna basmışız gibi)
    data = {
        'plakaKodu': str(city_code), # Kullanıcının girdiği il kodu (Örn: 34)
        'nobetTarihi': target_date,  # Kullanıcının seçtiği veya bugünün tarihi
        'btn': 'Sorgula',            # Formu tetikleyen buton
        'token': token               # Güvenlik token'ımız
    }

    # POST işlemi için başlıkları biraz güncelliyoruz (E-Devlet nereden geldiğimizi soruyor)
    post_headers = headers.copy()
    post_headers['Referer'] = url
    post_headers['Origin'] = 'https://www.turkiye.gov.tr'
    post_headers['Content-Type'] = 'application/x-www-form-urlencoded'

    # E-Devlet'e formumuzu POST ediyoruz (Gönderiyoruz)
    try:
        post_response = session.post(url + '?submit', data=data, headers=post_headers, verify=False)
        post_response.raise_for_status()
    except Exception as e:
        return {"error": f"E-Devlet'ten veri çekilemedi: {str(e)}"}

    # 3. ADIM: Sonuçları Parçalama (Scraping)
    # E-Devlet'ten dönen tablolu sayfayı parçalıyoruz
    post_soup = BeautifulSoup(post_response.text, 'html.parser')
    
    pharmacies = [] # Eczaneleri tutacağımız liste
    
    # HTML içindeki tabloyu (<table>) buluyoruz
    table = post_soup.find('table')
    
    if table:
        tbody = table.find('tbody')
        if tbody:
            # Tablodaki tüm satırları (<tr>) dönüyoruz
            rows = tbody.find_all('tr')
            for row in rows:
                # Sütunları (<td>) buluyoruz
                cols = row.find_all('td')
                
                # Eğer satırda en az 4 sütun varsa bu gerçek bir veri satırıdır
                if len(cols) >= 4:
                    name = cols[0].get_text(strip=True)      # 1. Sütun: Eczane Adı
                    district = cols[1].get_text(strip=True)  # 2. Sütun: İlçe
                    
                    # 3. Sütun: Telefon (İçinde gereksiz 'Ara' kelimesi geçiyor, temizliyoruz)
                    phone_raw = cols[2].get_text(" ", strip=True)
                    phone = phone_raw.replace('Ara', '').strip()
                    
                    # 4. Sütun: Adres
                    address = cols[3].get_text(strip=True)
                    
                    # 5. Sütun (Eğer varsa): Haritada göster linki + index
                    harita_index = None
                    if len(cols) >= 5:
                        map_a = cols[4].find('a')
                        if map_a and map_a.get('href'):
                            href = map_a.get('href')
                            parsed = urlparse(href)
                            params = parse_qs(parsed.query)
                            if 'index' in params:
                                try:
                                    harita_index = int(params['index'][0])
                                except Exception:
                                    pass

                    pharmacies.append({
                        "name": name,
                        "district": district,
                        "phone": phone,
                        "address": address,
                        "map_link": "",
                        "latitude": None,
                        "longitude": None,
                        "_harita_index": harita_index
                    })
    
    # Koordinatları paralel olarak harita sayfalarından çek
    harita_base = url
    harita_headers = headers.copy()
    harita_headers['Referer'] = url

    def fetch_coord(index):
        try:
            h_url = f"{harita_base}?harita=Goster&index={index}"
            hr = session.get(h_url, headers=harita_headers, verify=False, timeout=8)
            lat_m = re.search(r'latti\s*=\s*parseFloat\(([0-9.]+)\)', hr.text)
            lng_m = re.search(r'longi\s*=\s*parseFloat\(([0-9.]+)\)', hr.text)
            if lat_m and lng_m:
                return index, float(lat_m.group(1)), float(lng_m.group(1))
        except Exception:
            pass
        return index, None, None

    indices = [(i, p['_harita_index']) for i, p in enumerate(pharmacies) if p['_harita_index'] is not None]

    if indices:
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(fetch_coord, harita_idx): pharm_idx for pharm_idx, harita_idx in indices}
            coord_map = {}
            for future in as_completed(futures):
                pharm_idx = futures[future]
                _, lat, lng = future.result()
                coord_map[pharm_idx] = (lat, lng)

        for pharm_idx, (lat, lng) in coord_map.items():
            pharmacies[pharm_idx]['latitude'] = lat
            pharmacies[pharm_idx]['longitude'] = lng
            if lat and lng:
                pharmacies[pharm_idx]['map_link'] = f"https://www.google.com/maps?q={lat},{lng}"

    # _harita_index alanını temizle
    for p in pharmacies:
        p.pop('_harita_index', None)

    return {"pharmacies": pharmacies}


# Web sayfasının ana dizini (Tarayıcıdan girildiğinde index.html'i yükler)
@app.route('/')
def index():
    return render_template('index.html')


# Dışarıdan veya başka uygulamalardan istek atılacak adres: /api/pharmacies?city_code=34 gibisinden
@app.route('/api/pharmacies', methods=['GET'])
def get_pharmacies():
    # URL parametresinden 'city_code' ile (il kodu) değerini alıyoruz 
    city_code = request.args.get('city_code')
    
    # Kullanıcıdan tarih bilgisini de alıyoruz Örnek 27.04.2026
    target_date = request.args.get('date')
    
    # Eğer şehir kodu girilmemişse HATA (400) dönüdürmek hedeflendi
    if not city_code:
        return jsonify({"error": "Lütfen city_code (İl Plaka Kodu) parametresini gönderin"}), 400
    
    # Fonksiyonumuzu çağırıp veriyi çekiyoruz ....
    data = fetch_pharmacies(city_code, target_date)
    
    # Çekilen veriyi tamamen JSON formatında dışarıya veriyoruz! (Bu sayede React, Flutter, Mobil her yerden okunabilir)
    return jsonify(data)


# Eğer bu dosya doğrudan çalıştırılmışsa Flask sunucusunu başlat
if __name__ == '__main__':
    # debug=True: Kod değiştiğinde sunucu kendini yeniden başlatır (Geliştirme için iyi)
    app.run(debug=True, port=5000)

    