import os
import json
import pickle
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Google Drive API izinleri
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Proje root dizini
BASE_DIR = Path(__file__).resolve().parent.parent


def get_drive_service():
    """Google Drive servisini başlatır"""
    creds = None
    
    # Dosya yollarını absolute path olarak belirle
    token_path = BASE_DIR / 'token.pickle'
    credentials_path = BASE_DIR / 'credentials.json'

    # Token varsa yükle
    if token_path.exists():
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # Token yoksa veya geçersizse yenile
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=8080)

        # Token kaydet
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service


def create_folder(service, folder_name, parent_id=None):
    """Google Drive'da klasör oluşturur"""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    folder = service.files().create(body=file_metadata, fields='id, name').execute()
    return folder.get('id')


def find_folder(service, folder_name, parent_id=None):
    """Klasör var mı kontrol eder, varsa ID döner"""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    return items[0]['id'] if items else None


def upload_file(service, file_path, folder_id, file_name):
    """Dosyayı Google Drive'a yükler ve linkle erişime açar"""
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)

    created = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink, webContentLink, iconLink'
    ).execute()

    file_id = created['id']

    # 🔓 Herkese açık (read-only) izin ver
    try:
        service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'},
            fields='id'
        ).execute()

        # Güncel linkleri tekrar al
        created = service.files().get(
            fileId=file_id,
            fields='id, name, webViewLink, webContentLink, iconLink'
        ).execute()
    except Exception as e:
        print(f"Permission error: {e}")

    # Linkler
    view_link = created.get('webViewLink') or f"https://drive.google.com/file/d/{file_id}/view"
    download_link = created.get('webContentLink') or f"https://drive.google.com/uc?export=download&id={file_id}"

    return {
        'id': file_id,
        'name': created.get('name', file_name),
        'view': view_link,
        'download': download_link,
        'icon': created.get('iconLink'),
    }


def get_file_download_link(service, file_id):
    """Dosya indirme linki oluşturur"""
    file = service.files().get(
        fileId=file_id,
        fields='webContentLink, webViewLink'
    ).execute()
    return file.get('webContentLink') or file.get('webViewLink')


def delete_file(service, file_id):
    """Dosyayı siler"""
    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"Dosya silinemedi: {e}")
        return False


def ensure_anyone_reader_on_folder(service, folder_id):
    """Klasörü herkese açık yapar (isteğe bağlı)"""
    try:
        service.permissions().create(
            fileId=folder_id,
            body={'role': 'reader', 'type': 'anyone'},
            fields='id'
        ).execute()
        return True
    except Exception as e:
        print(f"Klasör izin hatası: {e}")
        return False
    
def delete_file_by_url(service, file_url):
    """Google Drive dosyasını URL'den sil"""
    try:
        # URL'den file ID'yi çıkar
        # Format: https://drive.google.com/file/d/FILE_ID/view?usp=drivesdk
        if '/file/d/' in file_url:
            file_id = file_url.split('/file/d/')[1].split('/')[0]
            service.files().delete(fileId=file_id).execute()
            print(f"✓ Dosya silindi: {file_id}")
            return True
    except Exception as e:
        print(f"✗ Dosya silinemedi: {e}")
        return False


# ==================== HIGH-LEVEL FOLDER UTILITIES ====================

def get_or_create_case_folder(service, praxis_name, auftragsnummer):
    """
    Google Drive'da case için klasör yapısını oluşturur:
    Labor/Dental Scans/[Praxis]/[Auftragsnummer]

    Args:
        service: Google Drive service
        praxis_name: Praxis adı
        auftragsnummer: Auftrag numarası

    Returns:
        str: Auftrag klasörünün ID'si
    """
    # Labor klasörü
    labor_folder = find_folder(service, 'Labor')
    if not labor_folder:
        labor_folder = create_folder(service, 'Labor')

    # Dental scans klasörü
    dental_scans_folder = find_folder(service, 'Dental scans', parent_id=labor_folder)
    if not dental_scans_folder:
        dental_scans_folder = create_folder(service, 'Dental scans', parent_id=labor_folder)

    # Praxis klasörü
    praxis_folder = find_folder(service, praxis_name, parent_id=dental_scans_folder)
    if not praxis_folder:
        praxis_folder = create_folder(service, praxis_name, parent_id=dental_scans_folder)

    # Auftrag klasörü
    auftrag_folder = find_folder(service, auftragsnummer, parent_id=praxis_folder)
    if not auftrag_folder:
        auftrag_folder = create_folder(service, auftragsnummer, parent_id=praxis_folder)

    return auftrag_folder


def get_or_create_muhasebe_folder(service, folder_type='gelir'):
    """
    Muhasebe klasörü oluşturur: Muhasebe/Gelir Faturalari veya Muhasebe/Gider Faturalari

    Args:
        service: Google Drive service
        folder_type: 'gelir' veya 'gider'

    Returns:
        str: Target klasörün ID'si
    """
    # Muhasebe ana klasörü
    muhasebe_folder = find_folder(service, 'muhasebe')
    if not muhasebe_folder:
        muhasebe_folder = create_folder(service, 'muhasebe')

    # Alt klasör adı
    folder_name = 'Gelir Faturalari' if folder_type == 'gelir' else 'Gider Faturalari'

    # Alt klasörü bul veya oluştur (hem büyük hem küçük harfle dene)
    target_folder = find_folder(service, folder_name, parent_id=muhasebe_folder)
    if not target_folder:
        target_folder = find_folder(service, folder_name.lower(), parent_id=muhasebe_folder)
    if not target_folder:
        target_folder = create_folder(service, folder_name, parent_id=muhasebe_folder)

    return target_folder


def get_or_create_shipment_folder(service, lab_name, auftragsnummer):
    """
    Shipment klasör yapısını oluşturur: Shipment/[Lab]/[Auftragsnummer]

    Args:
        service: Google Drive service
        lab_name: Labor adı
        auftragsnummer: Auftrag numarası

    Returns:
        str: Shipment klasörünün ID'si
    """
    # Shipment ana klasörü
    shipment_root = find_folder(service, 'Shipment')
    if not shipment_root:
        shipment_root = create_folder(service, 'Shipment')

    # Labor klasörü
    labor_folder = find_folder(service, lab_name, parent_id=shipment_root)
    if not labor_folder:
        labor_folder = create_folder(service, lab_name, parent_id=shipment_root)

    # Auftrag klasörü
    shipment_folder = find_folder(service, auftragsnummer, parent_id=labor_folder)
    if not shipment_folder:
        shipment_folder = create_folder(service, auftragsnummer, parent_id=labor_folder)

    return shipment_folder


def get_or_create_xml_folder(service):
    """
    XML klasörü oluşturur: Labor/XML

    Args:
        service: Google Drive service

    Returns:
        str: XML klasörünün ID'si
    """
    # Labor klasörü
    labor_folder = find_folder(service, 'Labor')
    if not labor_folder:
        labor_folder = create_folder(service, 'Labor')

    # XML klasörü
    xml_folder = find_folder(service, 'XML', parent_id=labor_folder)
    if not xml_folder:
        xml_folder = create_folder(service, 'XML', parent_id=labor_folder)

    return xml_folder


def get_or_create_archive_folder(service, belge_tipi=None, yil=None):
    """
    Arşiv klasör yapısını oluşturur: Zahntec/Archive

    Args:
        service: Google Drive service
        belge_tipi: Belge tipi (kullanılmıyor, geriye uyumluluk için)
        yil: Dosya yılı (kullanılmıyor, geriye uyumluluk için)

    Returns:
        str: Archive klasörünün ID'si
    """
    # Import burada yapılıyor (circular import önlemek için)
    from archive.models import ArsivinAyarlari
    ayarlar = ArsivinAyarlari.get_ayarlar()

    # Zahntec klasörünü bul - önce ayarlardaki ID'yi kontrol et
    zahntec_folder = ayarlar.zahntec_folder_id

    if not zahntec_folder:
        # ID yoksa klasör adına göre ara (büyük/küçük harf varyasyonlarıyla)
        zahntec_folder = find_folder(service, 'Zahntec')
        if not zahntec_folder:
            zahntec_folder = find_folder(service, 'zahntec')
        if not zahntec_folder:
            zahntec_folder = find_folder(service, 'ZAHNTEC')
        if not zahntec_folder:
            # Yoksa yeni oluştur
            zahntec_folder = create_folder(service, 'Zahntec')

        # Bulunan/oluşturulan ID'yi kaydet
        ayarlar.zahntec_folder_id = zahntec_folder
        ayarlar.save()

    # Archive klasörünü bul (büyük/küçük harf varyasyonlarıyla)
    archive_folder = find_folder(service, 'Archive', parent_id=zahntec_folder)
    if not archive_folder:
        archive_folder = find_folder(service, 'archive', parent_id=zahntec_folder)
    if not archive_folder:
        archive_folder = find_folder(service, 'ARCHIVE', parent_id=zahntec_folder)
    if not archive_folder:
        # Yoksa yeni oluştur
        archive_folder = create_folder(service, 'Archive', parent_id=zahntec_folder)

    return archive_folder
