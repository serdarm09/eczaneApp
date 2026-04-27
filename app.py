from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import datetime
import urllib3
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
                    
                    # 5. Sütun (Eğer varsa): Haritada göster linki
                    map_link = ""
                    if len(cols) >= 5:
                        map_a = cols[4].find('a')
                        if map_a and map_a.get('href'):
                            # Link "https" ile başlamadığı için başına turkiye.gov.tr ekliyoruz
                            map_link = "https://www.turkiye.gov.tr" + map_a.get('href')

                    # Temizlediğimiz veriyi bir Sözlük (Dictionary) objesi olarak listemize ekliyoruz
                    pharmacies.append({
                        "name": name,
                        "district": district,
                        "phone": phone,
                        "address": address,
                        "map_link": map_link
                    })
    
    # Sonuçları API'nin döndüreceği şekilde objeye çevirip geri dönüyoruz
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

    