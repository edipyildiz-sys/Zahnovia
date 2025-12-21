import os
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from utils.google_drive import get_drive_service, upload_file, get_or_create_archive_folder


def generate_declaration_pdf(declaration):
    """
    Declaration için PDF oluştur ve Google Drive'a yükle

    Args:
        declaration: Declaration instance

    Returns:
        dict: {'pdf_path': local_path, 'drive_url': google_drive_url}
    """
    # Hersteller profile bilgisini al
    try:
        hersteller_profile = declaration.praxis.hersteller_profile
    except:
        hersteller_profile = None

    # Debug: Tarihi yazdır
    print(f"DEBUG PDF - Declaration ID: {declaration.id}")
    print(f"DEBUG PDF - Herstellungsdatum: {declaration.herstellungsdatum}")
    print(f"DEBUG PDF - Herstellungsdatum type: {type(declaration.herstellungsdatum)}")
    
    # HTML render et
    html_string = render_to_string('declarations/pdf/declaration.html', {
        'declaration': declaration,
        'hersteller_profile': hersteller_profile
    })

    # PDF oluştur
    pdf_filename = f"{declaration.declaration_number}.pdf"
    pdf_dir = os.path.join(settings.BASE_DIR, 'temp_pdfs')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    HTML(string=html_string).write_pdf(pdf_path)

    # Google Drive'a yükle
    try:
        service = get_drive_service()

        # Zahnovia/Declarations klasörünü bul veya oluştur
        folder_id = get_or_create_declarations_folder(service)

        # Dosyayı yükle
        file_info = upload_file(
            service=service,
            file_path=pdf_path,
            folder_id=folder_id,
            file_name=pdf_filename
        )

        drive_url = file_info.get('view')

        # Local PDF'i sil (opsiyonel)
        # os.remove(pdf_path)

        return {
            'pdf_path': pdf_path,
            'drive_url': drive_url
        }
    except Exception as e:
        print(f"Google Drive upload error: {e}")
        return {
            'pdf_path': pdf_path,
            'drive_url': None
        }


def get_or_create_declarations_folder(service):
    """
    Google Drive'da Zahnovia/Declarations klasörünü bul veya oluştur
    """
    from utils.google_drive import find_folder, create_folder

    # Zahnovia ana klasörü
    zahnovia_folder = find_folder(service, 'Zahnovia')
    if not zahnovia_folder:
        zahnovia_folder = create_folder(service, 'Zahnovia')

    # Declarations alt klasörü
    declarations_folder = find_folder(service, 'Declarations', parent_id=zahnovia_folder)
    if not declarations_folder:
        declarations_folder = create_folder(service, 'Declarations', parent_id=zahnovia_folder)

    return declarations_folder


# ===== ARCHIVE GOOGLE DRIVE FUNCTIONS =====

def get_or_create_zahnovia_archive_folder(service):
    """
    Google Drive'da Zahnovia/Archive klasörünü bul veya oluştur
    """
    from utils.google_drive import find_folder, create_folder

    # Zahnovia ana klasörü
    zahnovia_folder = find_folder(service, 'Zahnovia')
    if not zahnovia_folder:
        zahnovia_folder = create_folder(service, 'Zahnovia')

    # Archive alt klasörü
    archive_folder = find_folder(service, 'Archive', parent_id=zahnovia_folder)
    if not archive_folder:
        archive_folder = create_folder(service, 'Archive', parent_id=zahnovia_folder)

    return archive_folder


def upload_to_drive(file, title, file_name):
    """
    Dosyayı Google Drive'a yükle (Archive için)
    
    Args:
        file: Django UploadedFile object
        title: Döküman başlığı
        file_name: Dosya adı
        
    Returns:
        dict: {'id': file_id, 'view': view_url} veya None
    """
    try:
        service = get_drive_service()
        
        # Archive klasörünü al
        folder_id = get_or_create_zahnovia_archive_folder(service)
        
        # Geçici dosya oluştur
        temp_dir = os.path.join(settings.BASE_DIR, 'temp_pdfs')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file_name)
        
        # Dosyayı geçici konuma kaydet
        with open(temp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Google Drive'a yükle
        file_info = upload_file(
            service=service,
            file_path=temp_path,
            folder_id=folder_id,
            file_name=file_name
        )
        
        # Geçici dosyayı sil
        try:
            os.remove(temp_path)
        except:
            pass
        
        return {
            'id': file_info.get('id'),
            'view': file_info.get('view')
        }
    except Exception as e:
        print(f"Google Drive upload error: {e}")
        return None


def delete_from_drive(file_id):
    """
    Google Drive'dan dosya sil
    
    Args:
        file_id: Google Drive file ID
        
    Returns:
        bool: Başarılı ise True
    """
    try:
        from utils.google_drive import delete_file
        service = get_drive_service()
        return delete_file(service, file_id)
    except Exception as e:
        print(f"Google Drive delete error: {e}")
        return False
