const CITIES = [
    { code: '1', name: 'ADANA' }, { code: '2', name: 'ADIYAMAN' }, { code: '3', name: 'AFYONKARAHİSAR' },
    { code: '4', name: 'AĞRI' }, { code: '68', name: 'AKSARAY' }, { code: '5', name: 'AMASYA' },
    { code: '6', name: 'ANKARA' }, { code: '7', name: 'ANTALYA' }, { code: '75', name: 'ARDAHAN' },
    { code: '8', name: 'ARTVİN' }, { code: '9', name: 'AYDIN' }, { code: '10', name: 'BALIKESİR' },
    { code: '74', name: 'BARTIN' }, { code: '72', name: 'BATMAN' }, { code: '69', name: 'BAYBURT' },
    { code: '11', name: 'BİLECİK' }, { code: '12', name: 'BİNGÖL' }, { code: '13', name: 'BİTLİS' },
    { code: '14', name: 'BOLU' }, { code: '15', name: 'BURDUR' }, { code: '16', name: 'BURSA' },
    { code: '17', name: 'ÇANAKKALE' }, { code: '18', name: 'ÇANKIRI' }, { code: '19', name: 'ÇORUM' },
    { code: '20', name: 'DENİZLİ' }, { code: '21', name: 'DİYARBAKIR' }, { code: '81', name: 'DÜZCE' },
    { code: '22', name: 'EDİRNE' }, { code: '23', name: 'ELAZIĞ' }, { code: '24', name: 'ERZİNCAN' },
    { code: '25', name: 'ERZURUM' }, { code: '26', name: 'ESKİŞEHİR' }, { code: '27', name: 'GAZİANTEP' },
    { code: '28', name: 'GİRESUN' }, { code: '29', name: 'GÜMÜŞHANE' }, { code: '30', name: 'HAKKARİ' },
    { code: '31', name: 'HATAY' }, { code: '76', name: 'IĞDIR' }, { code: '32', name: 'ISPARTA' },
    { code: '34', name: 'İSTANBUL' }, { code: '35', name: 'İZMİR' }, { code: '46', name: 'KAHRAMANMARAŞ' },
    { code: '78', name: 'KARABÜK' }, { code: '70', name: 'KARAMAN' }, { code: '36', name: 'KARS' },
    { code: '37', name: 'KASTAMONU' }, { code: '38', name: 'KAYSERİ' }, { code: '71', name: 'KIRIKKALE' },
    { code: '39', name: 'KIRKLARELİ' }, { code: '40', name: 'KIRŞEHİR' }, { code: '79', name: 'KİLİS' },
    { code: '41', name: 'KOCAELİ' }, { code: '42', name: 'KONYA' }, { code: '43', name: 'KÜTAHYA' },
    { code: '44', name: 'MALATYA' }, { code: '45', name: 'MANİSA' }, { code: '47', name: 'MARDİN' },
    { code: '33', name: 'MERSİN' }, { code: '48', name: 'MUĞLA' }, { code: '49', name: 'MUŞ' },
    { code: '50', name: 'NEVŞEHİR' }, { code: '51', name: 'NİĞDE' }, { code: '52', name: 'ORDU' },
    { code: '80', name: 'OSMANİYE' }, { code: '53', name: 'RİZE' }, { code: '54', name: 'SAKARYA' },
    { code: '55', name: 'SAMSUN' }, { code: '56', name: 'SİİRT' }, { code: '57', name: 'SİNOP' },
    { code: '58', name: 'SİVAS' }, { code: '63', name: 'ŞANLIURFA' }, { code: '73', name: 'ŞIRNAK' },
    { code: '59', name: 'TEKİRDAĞ' }, { code: '60', name: 'TOKAT' }, { code: '61', name: 'TRABZON' },
    { code: '62', name: 'TUNCELİ' }, { code: '64', name: 'UŞAK' }, { code: '65', name: 'VAN' },
    { code: '77', name: 'YALOVA' }, { code: '66', name: 'YOZGAT' }, { code: '67', name: 'ZONGULDAK' }
];

document.addEventListener('DOMContentLoaded', () => {
    const citySelect = document.getElementById('citySelect');
    const districtSelect = document.getElementById('districtSelect');
    const dateSelect = document.getElementById('dateSelect');
    const searchBtn = document.getElementById('searchBtn');
    const textSearchInput = document.getElementById('textSearchInput');

    const loadingSection = document.getElementById('loadingSection');
    const resultsSection = document.getElementById('resultsSection');
    const emptyState = document.getElementById('emptyState');
    const errorState = document.getElementById('errorState');

    const pharmaciesGrid = document.getElementById('pharmaciesGrid');
    const resultsCount = document.querySelector('.results-count');
    const errorMessage = document.getElementById('errorMessage');

    let allPharmacies = [];
    let currentDistricts = new Set();

    // Set today's date as default and minimum for date picker
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const todayStr = `${yyyy}-${mm}-${dd}`;

    dateSelect.min = todayStr;
    dateSelect.value = todayStr;

    // Sort and populate cities
    CITIES.sort((a, b) => a.name.localeCompare(b.name, 'tr')).forEach(city => {
        const option = document.createElement('option');
        option.value = city.code;
        option.textContent = city.name;
        citySelect.appendChild(option);
    });

    // Handle city and date selection to enable/disable search button
    function validateSearchForm() {
        if (citySelect.value && dateSelect.value) {
            searchBtn.disabled = false;
        } else {
            searchBtn.disabled = true;
        }
    }

    citySelect.addEventListener('change', () => {
        validateSearchForm();

        // Yeni bir il seçildiğinde eski arama verilerini ve ilçe seçimini anında sıfırla
        districtSelect.innerHTML = '<option value="" disabled selected>Önce şehir seçin...</option>';
        districtSelect.disabled = true;
        textSearchInput.value = '';
        hideAllStates();
    });

    dateSelect.addEventListener('input', validateSearchForm);
    dateSelect.addEventListener('change', validateSearchForm);

    // Initial validation
    validateSearchForm();

    // Handle district filtering
    districtSelect.addEventListener('change', () => {
        textSearchInput.value = ''; // Farklı ilçe seçilince arama kutusunu sıfırla
        applyFilters();
    });

    // Handle text search filtering
    textSearchInput.addEventListener('input', () => {
        applyFilters();
    });

    function applyFilters() {
        const selectedDistrict = districtSelect.value;
        const searchText = textSearchInput.value.toLowerCase();

        let filtered = allPharmacies;

        if (selectedDistrict !== 'all') {
            filtered = filtered.filter(p => p.district === selectedDistrict);
        }

        if (searchText) {
            filtered = filtered.filter(p =>
                p.name.toLowerCase().includes(searchText) ||
                p.address.toLowerCase().includes(searchText)
            );
        }

        renderPharmacies(filtered);
    }

    // Handle Search
    searchBtn.addEventListener('click', async () => {
        const cityCode = citySelect.value;
        const dateValue = dateSelect.value;

        if (!cityCode || !dateValue) {
            alert('Lütfen hem il hem de tarih seçtiğinizden emin olun.');
            return;
        }

        // Format date from YYYY-MM-DD to DD/MM/YYYY
        let formattedDate = '';
        if (dateSelect.value) {
            const parts = dateSelect.value.split('-');
            if (parts.length === 3) {
                formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
            }
        }

        // Reset UI
        hideAllStates();
        loadingSection.classList.remove('hidden');
        districtSelect.disabled = true;
        districtSelect.innerHTML = '<option value="" disabled selected>Yükleniyor...</option>';
        searchBtn.disabled = true;

        try {
            const url = `/api/pharmacies?city_code=${cityCode}${formattedDate ? `&date=${formattedDate}` : ''}`;
            const response = await fetch(url);
            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || 'Sunucu hatası oluştu');
            }


            allPharmacies = data.pharmacies || [];

            if (allPharmacies.length === 0) {
                hideAllStates();
                emptyState.classList.remove('hidden');
            } else {
                // Populate Districts
                currentDistricts.clear();
                allPharmacies.forEach(p => currentDistricts.add(p.district));

                populateDistricts(Array.from(currentDistricts).sort((a, b) => a.localeCompare(b, 'tr')));

                hideAllStates();
                textSearchInput.value = ''; // Reset text search on new city
                resultsSection.classList.remove('hidden');
                renderPharmacies(allPharmacies);
            }

        } catch (error) {
            console.error('Error fetching pharmacies:', error);
            hideAllStates();
            errorMessage.textContent = error.message;
            errorState.classList.remove('hidden');
        } finally {
            searchBtn.disabled = false;
        }
    });

    function hideAllStates() {
        loadingSection.classList.add('hidden');
        resultsSection.classList.add('hidden');
        emptyState.classList.add('hidden');
        errorState.classList.add('hidden');
    }

    function populateDistricts(districts) {
        districtSelect.innerHTML = '<option value="all">Tüm İlçeler</option>';
        districts.forEach(d => {
            const option = document.createElement('option');
            option.value = d;
            option.textContent = d;
            districtSelect.appendChild(option);
        });
        districtSelect.disabled = false;
    }

    function renderPharmacies(pharmacies) {
        pharmaciesGrid.innerHTML = '';
        resultsCount.textContent = `${pharmacies.length} Eczane`;

        if (pharmacies.length === 0) {
            hideAllStates();
            emptyState.classList.remove('hidden');
            return;
        }

        pharmacies.forEach(p => {
            const card = document.createElement('div');
            card.className = 'pharmacy-card';

            card.innerHTML = `
                <div class="card-header">
                    <h3 class="card-title">${p.name}</h3>
                    <span class="card-district">${p.district}</span>
                </div>
                <div class="card-body">
                    <div class="info-row">
                        <i class="ph-fill ph-map-pin"></i>
                        <span>${p.address}</span>
                    </div>
                    <div class="info-row">
                        <i class="ph-fill ph-phone"></i>
                        <span>${p.phone}</span>
                    </div>
                </div>
                <div class="card-actions">
                    <a href="tel:${p.phone.replace(/[^0-9]/g, '')}" class="btn-outline btn-call">
                        <i class="ph-fill ph-phone-call"></i> Ara
                    </a>
                    ${p.map_link ? `
                    <a href="${p.map_link}" target="_blank" class="btn-outline">
                        <i class="ph-fill ph-map-trifold"></i> Harita
                    </a>
                    ` : `
                    <a href="https://maps.google.com/?q=${encodeURIComponent(p.name + ' Eczanesi ' + p.district + ' ' + p.address)}" target="_blank" class="btn-outline">
                        <i class="ph-fill ph-map-trifold"></i> Harita
                    </a>
                    `}
                </div>
            `;

            pharmaciesGrid.appendChild(card);
        });
    }
});
