# Zahnovia - Praxis Verwaltungssystem

Konformitätserklärung (Uygunluk Beyanı) yönetim sistemi.

## Özellikler

- 🔐 **Login Sistemi**: Güvenli kullanıcı girişi
- 📊 **Dashboard**: İstatistikler ve özet bilgiler
- 📝 **Konformitätserklärung**: Uygunluk beyanı oluşturma
- 📋 **Beyan Listesi**: Tüm beyanları görüntüleme ve yönetme
- 🎨 **Modern UI**: Temiz ve kullanıcı dostu arayüz

## Kurulum

### 1. Projeyi Klonlayın

```bash
cd C:\Users\Edip\Zahnovia
```

### 2. Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 4. .env Dosyası

```bash
copy .env.example .env
```

### 5. Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Superuser Oluşturun

```bash
python manage.py createsuperuser
```

### 7. Sunucuyu Başlatın

```bash
python manage.py runserver
```

Tarayıcıda açın: http://127.0.0.1:8000/

## Kullanım

1. **Login**: Kullanıcı adı ve şifre ile giriş yapın
2. **Dashboard**: Ana sayfada istatistikleri görün
3. **Konformitätserklärung**: Soldaki menüden yeni beyan oluşturun
4. **Beyan Listesi**: Tüm beyanlarınızı görüntüleyin

## Proje Yapısı

```
Zahnovia/
├── app/                      # Django project settings
├── declarations/             # Beyan app'i
│   ├── models.py            # Declaration & DeclarationItem
│   ├── views.py             # View fonksiyonları
│   ├── forms.py             # Django forms
│   └── urls.py              # URL routing
├── mytemplates/             # HTML templates
│   ├── base.html           # Ana layout
│   ├── login.html          # Login sayfası
│   ├── dashboard.html      # Dashboard
│   └── declarations/       # Beyan templates
├── static/                  # CSS, JS, images
├── manage.py
└── requirements.txt
```

## Teknolojiler

- Django 5.2.7
- SQLite (development)
- Bootstrap (CSS framework)
- Font Awesome (icons)

## Geliştirme

Yeni özellikler eklemek için:

1. `declarations/models.py` - Yeni modeller
2. `declarations/views.py` - Yeni view'lar
3. `mytemplates/` - Yeni template'ler
4. `declarations/urls.py` - Yeni URL pattern'ler

---

© 2025 Zahnovia - Praxis Verwaltungssystem
