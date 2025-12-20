from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import HttpResponse
from datetime import date, datetime
from .models import Declaration, DeclarationItem, MaterialProduct, HerstellerProfile, ProductWork
from .forms import DeclarationItemFormSet, ProductWorkFormSet
from .utils import generate_declaration_pdf


def user_login(request):
    """Login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
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
    declarations = Declaration.objects.filter(praxis=request.user)
    return render(request, 'declarations/declaration_list.html', {'declarations': declarations})


@login_required
def declaration_create(request):
    """Yeni beyan oluştur"""
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
        material_formset = DeclarationItemFormSet(request.POST, instance=declaration, prefix='materials')

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
            messages.error(request, 'Formda hatalar var, lütfen kontrol edin.')
    else:
        # Boş bir declaration oluştur (geçici)
        declaration = Declaration(praxis=request.user)
        product_work_formset = ProductWorkFormSet(instance=declaration, prefix='product_works')
        material_formset = DeclarationItemFormSet(instance=declaration, prefix='materials')

    # MaterialProduct'ları ve Hersteller Profile'ı gönder
    material_products = MaterialProduct.objects.filter(is_active=True)

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
def declaration_detail(request, pk):
    """Beyan detay sayfası"""
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
    products = MaterialProduct.objects.filter(user=request.user).order_by('name')
    return render(request, 'declarations/material_products.html', {'products': products})


@login_required
def material_product_create(request):
    """Yeni material product oluştur"""
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
