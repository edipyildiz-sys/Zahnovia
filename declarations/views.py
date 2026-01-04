from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from datetime import date, datetime
from django.db.models import Q
from django import forms
from .models import Declaration, DeclarationItem, MaterialProduct, HerstellerProfile, ProductWork, ArchiveDocument
from .forms import DeclarationItemFormSet, ProductWorkFormSet, DeclarationItemForm, ProductWorkForm, BaseDeclarationItemFormSet
from .utils import generate_declaration_pdf, parse_declaration_pdf
from django.views.decorators.http import require_POST


def user_login(request):
    """Login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Superuser ise admin'e yönlendir
            if user.is_superuser:
                return redirect('/admin/')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, 'Ungültige Anmeldedaten')
    return render(request, 'login.html')


def user_logout(request):
    """Logout view"""
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    """Dashboard - Ana sayfa"""
    # Superuser ise admin'e yönlendir
    if request.user.is_superuser:
        return redirect('/admin/')
    
    total_declarations = Declaration.objects.filter(praxis=request.user).count()
    recent_declarations = Declaration.objects.filter(praxis=request.user)[:5]

    context = {
        'total_declarations': total_declarations,
        'recent_declarations': recent_declarations,
    }
    return render(request, 'dashboard.html', context)


@login_required
def declaration_list(request):
    """Tüm beyanların listesi"""
    # Superuser admin sayfasına erişemez
    if request.user.is_superuser:
        return redirect('/admin/')
    
    declarations = Declaration.objects.filter(praxis=request.user)
    return render(request, 'declarations/declaration_list.html', {'declarations': declarations})


@login_required
def declaration_create(request):
    """Yeni beyan oluştur"""
    # Superuser admin sayfasına erişemez
    if request.user.is_superuser:
        return redirect('/admin/')
    
    if request.method == 'POST':
        # Form verilerini al
        auftragsnummer = request.POST.get('auftragsnummer')
        patient_name = request.POST.get('patient_name')
        herstellungsdatum_str = request.POST.get('herstellungsdatum')
        
        # String'i date objesine çevir
        if herstellungsdatum_str:
            try:
                herstellungsdatum = datetime.strptime(herstellungsdatum_str, '%Y-%m-%d').date()
            except ValueError:
                herstellungsdatum = date.today()
        else:
            herstellungsdatum = date.today()
        
        print(f"DEBUG - Herstellungsdatum from form: {herstellungsdatum_str}")
        print(f"DEBUG - Herstellungsdatum to save: {herstellungsdatum} (type: {type(herstellungsdatum)})")

        # Declaration oluştur
        declaration = Declaration.objects.create(
            praxis=request.user,
            auftragsnummer=auftragsnummer,
            patient_name=patient_name,
            herstellungsdatum=herstellungsdatum
        )

        # Form verilerini işle
        product_work_formset = ProductWorkFormSet(request.POST, instance=declaration, prefix='product_works')
        material_formset = DeclarationItemFormSet(request.POST, instance=declaration, prefix='materials', user=request.user)

        if product_work_formset.is_valid() and material_formset.is_valid():
            # Product works'leri kaydet
            product_works = product_work_formset.save(commit=False)
            for i, pw in enumerate(product_works, start=1):
                pw.line_number = i
                pw.save()

            # Materials'ları kaydet
            items = material_formset.save(commit=False)
            for i, item in enumerate(items, start=1):
                item.line_number = i
                item.save()

            # PDF oluştur ve Google Drive'a yükle
            try:
                result = generate_declaration_pdf(declaration)
                if result.get('drive_url'):
                    declaration.pdf_url = result['drive_url']
                    declaration.save()
                    messages.success(request, f'Beyan {declaration.declaration_number} başarıyla oluşturuldu ve Google Drive\'a yüklendi!')
                else:
                    messages.warning(request, f'Beyan {declaration.declaration_number} oluşturuldu ama Google Drive yüklemesi başarısız oldu.')
            except Exception as e:
                messages.warning(request, f'Beyan oluşturuldu ama PDF hatası: {str(e)}')

            return redirect('declaration_detail', pk=declaration.pk)
        else:
            declaration.delete()  # Hata varsa declaration'ı sil

            # Debug: Form hatalarını göster
            print("=" * 80)
            print("FORM VALIDATION ERRORS:")
            print("=" * 80)
            print("Product Work Formset Valid:", product_work_formset.is_valid())
            print("Product Work Errors:", product_work_formset.errors)
            print("Material Formset Valid:", material_formset.is_valid())
            print("Material Errors:", material_formset.errors)
            print("=" * 80)

            messages.error(request, 'Formda hatalar var, lütfen kontrol edin.')
    else:
        # Boş bir declaration oluştur (geçici)
        declaration = Declaration(praxis=request.user)
        product_work_formset = ProductWorkFormSet(instance=declaration, prefix='product_works')
        material_formset = DeclarationItemFormSet(instance=declaration, prefix='materials', user=request.user)

    # MaterialProduct'ları ve Hersteller Profile'ı gönder (sadece kullanıcının kendi ürünleri)
    material_products = MaterialProduct.objects.filter(user=request.user, is_active=True)

    try:
        hersteller_profile = request.user.hersteller_profile
    except HerstellerProfile.DoesNotExist:
        hersteller_profile = None

    return render(request, 'declarations/declaration_create.html', {
        'product_work_formset': product_work_formset,
        'material_formset': material_formset,
        'material_products': material_products,
        'hersteller_profile': hersteller_profile
    })


@login_required
def declaration_edit(request, pk):
    """Beyan düzenle"""
    if request.user.is_superuser:
        return redirect('/admin/')

    declaration = get_object_or_404(Declaration, pk=pk, praxis=request.user)

    if request.method == 'POST':
        # Form verilerini al
        declaration.auftragsnummer = request.POST.get('auftragsnummer')
        declaration.patient_name = request.POST.get('patient_name')
        herstellungsdatum_str = request.POST.get('herstellungsdatum')

        if herstellungsdatum_str:
            try:
                declaration.herstellungsdatum = datetime.strptime(herstellungsdatum_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        declaration.save()

        # Formset'leri işle
        product_work_formset = ProductWorkFormSet(request.POST, instance=declaration, prefix='product_works')
        material_formset = DeclarationItemFormSet(request.POST, instance=declaration, prefix='materials', user=request.user)

        if product_work_formset.is_valid() and material_formset.is_valid():
            # Mevcut product works'leri sil
            declaration.product_works.all().delete()
            # Yeni product works'leri kaydet
            product_works = product_work_formset.save(commit=False)
            for i, pw in enumerate(product_works, start=1):
                pw.line_number = i
                pw.save()

            # Mevcut materials'ı sil
            declaration.items.all().delete()
            # Yeni materials'ı kaydet
            items = material_formset.save(commit=False)
            for i, item in enumerate(items, start=1):
                item.line_number = i
                item.save()

            # Eski PDF'i Google Drive'dan sil
            if declaration.pdf_url:
                try:
                    from .utils import delete_from_drive
                    # URL'den file ID'yi çıkar
                    if '/d/' in declaration.pdf_url:
                        file_id = declaration.pdf_url.split('/d/')[1].split('/')[0]
                        delete_from_drive(file_id)
                        print(f"Eski PDF silindi: {file_id}")
                except Exception as e:
                    print(f"Eski PDF silinirken hata: {str(e)}")

            # PDF'i yeniden oluştur ve yükle
            try:
                result = generate_declaration_pdf(declaration)
                if result.get('drive_url'):
                    declaration.pdf_url = result['drive_url']
                    declaration.save()
                    messages.success(request, f'Beyan {declaration.declaration_number} başarıyla güncellendi ve PDF yenilendi!')
                else:
                    messages.warning(request, 'Beyan güncellendi ama PDF yüklemesi başarısız oldu.')
            except Exception as e:
                messages.warning(request, f'Beyan güncellendi ama PDF hatası: {str(e)}')

            return redirect('declaration_detail', pk=declaration.pk)
        else:
            messages.error(request, 'Formda hatalar var, lütfen kontrol edin.')
    else:
        # Edit için extra=0 kullan (boş satır ekleme)
        ProductWorkFormSetEdit = forms.inlineformset_factory(
            Declaration, ProductWork, form=ProductWorkForm,
            extra=0, max_num=20, can_delete=True
        )
        DeclarationItemFormSetEdit = forms.inlineformset_factory(
            Declaration, DeclarationItem, form=DeclarationItemForm,
            formset=BaseDeclarationItemFormSet, extra=0, max_num=20, can_delete=True
        )

        product_work_formset = ProductWorkFormSetEdit(instance=declaration, prefix='product_works')
        material_formset = DeclarationItemFormSetEdit(instance=declaration, prefix='materials', user=request.user)

    # MaterialProduct'ları ve Hersteller Profile'ı gönder
    material_products = MaterialProduct.objects.filter(user=request.user, is_active=True)

    try:
        hersteller_profile = request.user.hersteller_profile
    except HerstellerProfile.DoesNotExist:
        hersteller_profile = None

    return render(request, 'declarations/declaration_edit.html', {
        'declaration': declaration,
        'product_work_formset': product_work_formset,
        'material_formset': material_formset,
        'material_products': material_products,
        'hersteller_profile': hersteller_profile
    })


@login_required
def declaration_detail(request, pk):
    """Beyan detay sayfası"""
    # Superuser admin sayfasına erişemez
    if request.user.is_superuser:
        return redirect('/admin/')

    declaration = get_object_or_404(Declaration, pk=pk, praxis=request.user)

    # Hersteller profile bilgisini al
    try:
        hersteller_profile = request.user.hersteller_profile
    except HerstellerProfile.DoesNotExist:
        hersteller_profile = None

    return render(request, 'declarations/declaration_detail.html', {
        'declaration': declaration,
        'hersteller_profile': hersteller_profile
    })


@login_required
def material_products_list(request):
    """Material Products listesi - Sadece kullanıcının malzemeleri"""
    # Superuser admin sayfasına erişemez
    if request.user.is_superuser:
        return redirect('/admin/')
    
    products = MaterialProduct.objects.filter(user=request.user).order_by('name')
    return render(request, 'declarations/material_products.html', {'products': products})


@login_required
def material_product_create(request):
    """Yeni material product oluştur"""
    # Superuser admin sayfasına erişemez
    if request.user.is_superuser:
        return redirect('/admin/')
    
    if request.method == 'POST':
        material = request.POST.get('material')
        firma = request.POST.get('firma')
        bestandteile = request.POST.get('bestandteile')
        ce_status = request.POST.get('ce_status', 'Ja')

        # Name field'ı otomatik oluştur (Material + Firma kombinasyonu)
        name = f"{material} - {firma}"

        MaterialProduct.objects.create(
            user=request.user,
            name=name,
            material=material,
            firma=firma,
            bestandteile=bestandteile,
            material_lot_no='',  # Lot No artık declaration create'de girilecek
            ce_status=ce_status,
            device_identification=''
        )
        messages.success(request, f'Material Product "{name}" başarıyla oluşturuldu!')
        return redirect('material_products_list')

    return render(request, 'declarations/material_product_create.html')


@login_required
def material_product_delete(request, pk):
    """Material product sil"""
    product = get_object_or_404(MaterialProduct, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f'Material Product "{name}" silindi!')
    return redirect('material_products_list')


@login_required
def hersteller_profile(request):
    """Hersteller profil bilgileri"""
    # Superuser admin sayfasına erişemez
    if request.user.is_superuser:
        return redirect('/admin/')
    
    try:
        profile = request.user.hersteller_profile
    except HerstellerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        if profile:
            # Güncelle
            profile.firma_name = request.POST.get('firma_name')
            profile.strasse = request.POST.get('strasse')
            profile.plz = request.POST.get('plz')
            profile.ort = request.POST.get('ort')
            profile.telefon = request.POST.get('telefon')
            profile.email = request.POST.get('email')
            profile.verordnender_arzt = request.POST.get('verordnender_arzt', '')
            profile.save()
            messages.success(request, 'Hersteller Profil güncellendi!')
        else:
            # Yeni oluştur
            HerstellerProfile.objects.create(
                user=request.user,
                firma_name=request.POST.get('firma_name'),
                strasse=request.POST.get('strasse'),
                plz=request.POST.get('plz'),
                ort=request.POST.get('ort'),
                telefon=request.POST.get('telefon'),
                email=request.POST.get('email'),
                verordnender_arzt=request.POST.get('verordnender_arzt', '')
            )
            messages.success(request, 'Hersteller Profil oluşturuldu!')
        return redirect('hersteller_profile')

    return render(request, 'declarations/hersteller_profile.html', {'profile': profile})

# ===== ARCHIV VIEWS =====

@login_required
def archive_list(request):
    """Archiv Dokumentenliste"""
    if request.user.is_superuser:
        return redirect('/admin/')
    
    documents = ArchiveDocument.objects.filter(user=request.user).order_by('-document_date', '-upload_date')
    
    # Kategoriye göre filtrele
    category = request.GET.get('category')
    if category:
        documents = documents.filter(category=category)
    
    # Arama
    search = request.GET.get('search')
    if search:
        documents = documents.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(file_name__icontains=search) |
            Q(custom_category__icontains=search) |
            Q(category__icontains=search)
        )
    
    # Kullanıcının özel kategorilerini al
    custom_categories = ArchiveDocument.objects.filter(
        user=request.user,
        custom_category__isnull=False
    ).exclude(custom_category='').values_list('custom_category', flat=True).distinct().order_by('custom_category')

    context = {
        'documents': documents,
        'categories': ArchiveDocument.CATEGORY_CHOICES,
        'custom_categories': list(custom_categories),
        'selected_category': category,
        'search_query': search
    }
    
    return render(request, 'declarations/archive/archive_list.html', context)


@login_required
def archive_upload(request):
    """Archiv Dokument hochladen"""
    if request.user.is_superuser:
        return redirect('/admin/')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        category = request.POST.get('category', 'other')
        new_category_name = request.POST.get("new_category_name", "").strip()
        document_date_str = request.POST.get('document_date', '')
        file = request.FILES.get('file')
        
        # Belge tarihini parse et
        document_date = None
        if document_date_str:
            try:
                document_date = datetime.strptime(document_date_str, '%Y-%m-%d').date()
            except:
                pass
        
        if not file:
            messages.error(request, 'Bitte wählen Sie eine Datei aus.')
            return redirect('archive_list')
        
        # PDF kontrolü
        if not file.name.lower().endswith('.pdf'):
            messages.error(request, 'Nur PDF-Dateien sind erlaubt.')
            return redirect('archive_list')
        

        # Yeni veya özel kategori
        custom_cat = None
        if category == "__new__" and new_category_name:
            category = "other"
            custom_cat = new_category_name
        elif category.startswith('custom_'):
            # Dropdown'dan seçilen özel kategori
            custom_cat = category.replace('custom_', '')
            category = "other"

        # Belge oluştur
        document = ArchiveDocument.objects.create(
            user=request.user,
            title=title,
            description=description,
            category=category,
            custom_category=custom_cat or '',
            document_date=document_date,
            file_name=file.name
        )
        
        # Google Drive'a yükle
        try:
            from .utils import upload_to_drive
            result = upload_to_drive(file, title, file.name)
            
            if result:
                document.drive_file_id = result.get('id', '')
                document.drive_url = result.get('view', '')
                document.save()
                messages.success(request, f'Dokument "{title}" wurde erfolgreich hochgeladen!')
            else:
                document.delete()
                messages.error(request, 'Fehler beim Hochladen zu Google Drive.')
        except Exception as e:
            document.delete()
            messages.error(request, f'Fehler: {str(e)}')
            return redirect('archive_upload')
        
        return redirect('archive_list')
    
    return render(request, 'declarations/archive/archive_upload.html', {
        'categories': ArchiveDocument.CATEGORY_CHOICES
    })


@login_required
def archive_view(request, pk):
    """Archiv Dokument anzeigen"""
    if request.user.is_superuser:
        return redirect('/admin/')
    
    document = get_object_or_404(ArchiveDocument, pk=pk, user=request.user)
    
    return render(request, 'declarations/archive/archive_view.html', {
        'document': document
    })


@login_required
def archive_delete(request, pk):
    """Archiv Dokument löschen"""
    if request.user.is_superuser:
        return redirect('/admin/')
    
    document = get_object_or_404(ArchiveDocument, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Google Drive'dan sil
        if document.drive_file_id:
            try:
                from .utils import delete_from_drive
                delete_from_drive(document.drive_file_id)
            except Exception as e:
                messages.warning(request, f'Warnung: Fehler beim Löschen von Google Drive: {str(e)}')
        
        title = document.title
        document.delete()
        messages.success(request, f'Dokument "{title}" wurde gelöscht!')
        return redirect('archive_list')

    return render(request, 'declarations/archive/archive_delete.html', {
        'document': document
    })


@login_required
@require_POST
def parse_reference_pdf(request):
    """
    AJAX endpoint: Referans PDF dosyasını parse et ve JSON olarak döndür
    """
    if 'pdf_file' not in request.FILES:
        return JsonResponse({'error': 'Keine PDF-Datei hochgeladen'}, status=400)

    pdf_file = request.FILES['pdf_file']

    # Dosya türünü kontrol et
    if not pdf_file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'Nur PDF-Dateien sind erlaubt'}, status=400)

    # PDF'i parse et
    parsed_data = parse_declaration_pdf(pdf_file)

    # Hata kontrolü
    if 'error' in parsed_data:
        return JsonResponse({'error': parsed_data['error']}, status=400)

    # Debug: Print parsed data
    print("=" * 80)
    print("DEBUG: PARSED DATA TO RETURN")
    print("=" * 80)
    print(f"Auftragsnummer: {parsed_data.get('auftragsnummer')}")
    print(f"Patient Name: {parsed_data.get('patient_name')}")
    print(f"Herstellungsdatum: {parsed_data.get('herstellungsdatum')}")
    print(f"Product Works: {parsed_data.get('product_works')}")
    print(f"Materials: {parsed_data.get('materials')}")
    print("=" * 80)

    return JsonResponse(parsed_data)
