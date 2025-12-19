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
