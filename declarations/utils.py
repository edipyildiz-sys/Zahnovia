import os
import re
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from utils.google_drive import get_drive_service, upload_file, get_or_create_archive_folder
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


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


def parse_declaration_pdf(pdf_file):
    """
    Referans PDF dosyasından konformitätserklärung bilgilerini çıkar

    Args:
        pdf_file: Django UploadedFile object (PDF)

    Returns:
        dict: Parse edilmiş veriler
        {
            'auftragsnummer': str,
            'patient_name': str,
            'herstellungsdatum': str (YYYY-MM-DD),
            'product_works': [
                {'produktbezeichnung_arbeit': str, 'zahnnummer': str, 'zahnfarbe': str},
                ...
            ],
            'materials': [
                {'material': str, 'firma': str, 'bestandteile': str, 'material_lot_no': str, 'ce_status': str},
                ...
            ]
        }
    """
    if not PyPDF2:
        return {'error': 'PyPDF2 kütüphanesi yüklü değil'}

    try:
        # PDF'i oku
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""

        # Tüm sayfaları oku
        for page in pdf_reader.pages:
            text += page.extract_text()

        # Unicode karakterleri temizle
        text = text.replace('\u200b', '')  # Zero-width space
        text = text.replace('\ufeff', '')  # BOM

        # Debug: PDF'den çıkan metni logla
        try:
            print("=" * 80)
            print("DEBUG: PDF TEXT CONTENT")
            print("=" * 80)
            print(text.encode('utf-8', errors='replace').decode('utf-8'))
            print("=" * 80)
        except Exception as e:
            print(f"Debug print error: {e}")

        # Veriyi parse et
        parsed_data = {
            'auftragsnummer': '',
            'patient_name': '',
            'herstellungsdatum': '',
            'product_works': [],
            'materials': []
        }

        # Auftragsnummer çıkar (sadece standart format varsa)
        # Dentsply PDF'de Auftragsnummer yok, kullanıcı manuel girecek
        auftrag_match = re.search(r'Auftragsnummer[:\s]+([A-Z0-9-]+)', text, re.IGNORECASE)
        if auftrag_match:
            parsed_data['auftragsnummer'] = auftrag_match.group(1).strip()

        # Patient name çıkar
        # Dentsply gerçek format: "1Sanli,Seda Fischer,Christine Unknown Krone 24 Hoch"
        # Boşluklarla ayrılmış: ID Zahnarzt Patient Techniker Elementtyp Zahnnummer Produktion
        # Virgülden sonra boşluk YOK: "Fischer,Christine"
        patient_table_match = re.search(r'\d+[A-Za-zäöüßÄÖÜ]+,[A-Za-zäöüßÄÖÜ]+\s+([A-Za-zäöüßÄÖÜ]+),([A-Za-zäöüßÄÖÜ]+)\s+', text)
        if patient_table_match:
            # Virgülden sonra boşluk ekle
            parsed_data['patient_name'] = f"{patient_table_match.group(1)}, {patient_table_match.group(2)}"
        else:
            # Standart format: "Patientenname: Fischer, Christine"
            patient_match = re.search(r'Patient(?:enname)?[:\s]+([^\n]+)', text, re.IGNORECASE)
            if patient_match:
                parsed_data['patient_name'] = patient_match.group(1).strip()

        # Herstellungsdatum çıkar
        # Dentsply'de: "Erstellungsdatum: 01.01.2026 22:27:05" → Zahnovia'da "Herstellungsdatum"
        date_match = re.search(r'Erstellungsdatum[:\s]+(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})', text, re.IGNORECASE)
        if date_match:
            day, month, year = date_match.groups()
            parsed_data['herstellungsdatum'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        else:
            # Alternatif: standart "Herstellungsdatum" formatı
            date_match2 = re.search(r'Herstellungsdatum[:\s]+(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})', text, re.IGNORECASE)
            if date_match2:
                day, month, year = date_match2.groups()
                parsed_data['herstellungsdatum'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # Produktbezeichnung/Arbeit tablosunu çıkar
        # Dentsply Format: Tabloda "Elementtyp | Zahnnummer"
        # Zahnovia'da: "Produktbezeichnung / Arbeit | Zahnnummer | Zahnfarbe"

        # Format 1: Standart table format
        product_pattern = r'([^\|]+)\s*\|\s*(\d+[,\s]*\d*)\s*\|\s*([A-Z0-9]+)'
        product_matches = re.findall(product_pattern, text)

        for match in product_matches:
            if len(match) == 3:
                parsed_data['product_works'].append({
                    'produktbezeichnung_arbeit': match[0].strip(),
                    'zahnnummer': match[1].strip(),
                    'zahnfarbe': match[2].strip()
                })

        # Format 2: Dentsply Sirona tablosu
        # Gerçek format: "1Sanli,Seda Fischer,Christine Unknown Krone 24 Hoch"
        # Boşluklarla ayrılmış: ID Zahnarzt Patient Techniker Elementtyp Zahnnummer Produktion
        if not parsed_data['product_works']:
            # Pattern: ID Zahnarzt Patient Techniker Elementtyp Zahnnummer
            # Virgülden sonra boşluk olmayabilir: "Fischer,Christine" (boşluksuz)
            table_row_pattern = r'\d+[A-Za-zäöüßÄÖÜ]+,[A-Za-zäöüßÄÖÜ]+\s+[A-Za-zäöüßÄÖÜ]+,[A-Za-zäöüßÄÖÜ]+\s+[A-Za-zäöüßÄÖÜ]+\s+([A-Za-zäöüßÄÖÜ]+(?:\s+[A-Za-zäöüßÄÖÜ]+)*)\s+(\d+)'
            table_match = re.search(table_row_pattern, text)

            if table_match:
                elementtyp = table_match.group(1).strip()
                zahnnummer = table_match.group(2).strip()

                parsed_data['product_works'].append({
                    'produktbezeichnung_arbeit': elementtyp,  # Krone, Brücke, etc.
                    'zahnnummer': zahnnummer,  # 24, etc.
                    'zahnfarbe': ''  # Dentsply'de zahnfarbe yok
                })

        # Materialien tablosunu çıkar
        # Dentsply Format:
        #   Werkstückname: CERECMTLZirconia
        #   20260101-222705  <- Bu LOT NO (Material Lot No)
        #   Hersteller: DentsplySirona
        #   Materialname: CERECMTLZirconia

        # Material LOT NO çıkar
        # Format: "20260101-222705" -> Sadece son 6 hane: "222705"
        lot_no_match = re.search(r'\d{8}-(\d{6})', text)
        material_lot_no = lot_no_match.group(1).strip() if lot_no_match else ''

        # Materialname ve Hersteller (boşluksuz format)
        materialname_match = re.search(r'Materialname[:\s]*([A-Za-z0-9]+)', text, re.IGNORECASE)
        hersteller_match = re.search(r'Hersteller[:\s]*([A-Za-z]+)', text, re.IGNORECASE)

        if materialname_match:
            # Material adını düzenle: "CERECMTLZirconia" → "CEREC MTL Zirconia"
            material_name = materialname_match.group(1).strip()
            # CEREC, MTL, Zirconia gibi kelimeleri ayır
            material_name = re.sub(r'([A-Z][a-z]+)', r' \1', material_name).strip()
            material_name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', material_name).strip()

            # Hersteller adını düzenle: "DentsplySirona" → "Dentsply Sirona"
            firma_name = 'Dentsply Sirona'
            if hersteller_match:
                firma_raw = hersteller_match.group(1).strip()
                # DentsplySirona → Dentsply Sirona
                firma_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', firma_raw)

            material_data = {
                'material': material_name,
                'firma': firma_name,
                'bestandteile': '',
                'material_lot_no': material_lot_no,
                'ce_status': 'yes'
            }
            parsed_data['materials'].append(material_data)

        # Format 2: CE işareti, firma isimleri vb. ara (eski format)
        if not parsed_data['materials']:
            material_lines = text.split('\n')

            for i, line in enumerate(material_lines):
                # CE işareti içeren satırları ara
                if 'CE' in line or 'Lot' in line or 'Zirconi' in line:
                    # Material bilgisini parse et
                    parts = re.split(r'\s{2,}|\t', line)  # 2+ boşluk veya tab ile böl
                    if len(parts) >= 1:
                        material_data = {
                            'material': '',
                            'firma': '',
                            'bestandteile': '',
                            'material_lot_no': '',
                            'ce_status': 'yes' if 'CE' in line else 'no'
                        }

                        # İlk kısım genelde material
                        material_data['material'] = parts[0].strip()

                        # Firma ve diğer bilgileri çıkarmaya çalış
                        for part in parts[1:]:
                            if 'Lot' in part or 'LOT' in part:
                                lot_match = re.search(r'(?:Lot|LOT)[:\s]*([A-Z0-9-]+)', part)
                                if lot_match:
                                    material_data['material_lot_no'] = lot_match.group(1)
                            elif len(part) > 2 and material_data['firma'] == '':
                                material_data['firma'] = part.strip()

                        if material_data['material']:
                            parsed_data['materials'].append(material_data)

        return parsed_data

    except Exception as e:
        return {'error': f'PDF parse hatası: {str(e)}'}
