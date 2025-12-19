from django.db import models
from django.contrib.auth.models import User


class HerstellerProfile(models.Model):
    """Hersteller (Üretici) Profil Bilgileri - Kullanıcı başına bir tane"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='hersteller_profile')

    # Firma bilgileri
    firma_name = models.CharField(max_length=200, verbose_name="Firma Adı")
    strasse = models.CharField(max_length=200, verbose_name="Straße")
    plz = models.CharField(max_length=10, verbose_name="PLZ")
    ort = models.CharField(max_length=100, verbose_name="Ort")

    # İletişim bilgileri
    telefon = models.CharField(max_length=50, verbose_name="Telefon")
    email = models.EmailField(verbose_name="E-Mail")

    # Verordnender Arzt
    verordnender_arzt = models.CharField(max_length=200, verbose_name="Verordnender Arzt", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hersteller Profil'
        verbose_name_plural = 'Hersteller Profile'

    def __str__(self):
        return f"{self.firma_name} ({self.user.username})"


class Declaration(models.Model):
    """Konformitätserklärung (Uygunluk Beyanı)"""

    praxis = models.ForeignKey(User, on_delete=models.CASCADE, related_name='declarations')
    declaration_number = models.CharField(max_length=50, unique=True, blank=True)

    # Hasta ve Üretim Bilgileri
    auftragsnummer = models.CharField(max_length=100, verbose_name="Auftragsnummer", blank=True)
    patient_name = models.CharField(max_length=200, verbose_name="Patientenname")
    herstellungsdatum = models.DateField(verbose_name="Herstellungsdatum")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # PDF URL (oluşturulduktan sonra)
    pdf_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Konformitätserklärung'
        verbose_name_plural = 'Konformitätserklärungen'

    def __str__(self):
        return f"{self.declaration_number or 'Draft'} - {self.praxis.username}"

    def save(self, *args, **kwargs):
        if not self.declaration_number:
            # Otomatik numara üretimi: DECL-YYYY-NNNN
            from datetime import datetime
            year = datetime.now().year
            last_decl = Declaration.objects.filter(
                declaration_number__startswith=f'DECL-{year}'
            ).order_by('-declaration_number').first()

            if last_decl and last_decl.declaration_number:
                last_num = int(last_decl.declaration_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.declaration_number = f'DECL-{year}-{new_num:04d}'

        super().save(*args, **kwargs)


class ProductWork(models.Model):
    """Produktbezeichnung / Arbeit satırları"""

    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE, related_name='product_works')
    line_number = models.IntegerField(default=1)

    produktbezeichnung_arbeit = models.CharField(max_length=200, verbose_name="Produktbezeichnung / Arbeit")
    zahnnummer = models.CharField(max_length=100, verbose_name="Zahnnummer", blank=True)
    zahnfarbe = models.CharField(max_length=100, verbose_name="Zahnfarbe", blank=True)

    class Meta:
        ordering = ['line_number']
        verbose_name = 'Produktbezeichnung'
        verbose_name_plural = 'Produktbezeichnungen'

    def __str__(self):
        return f"{self.line_number}. {self.produktbezeichnung_arbeit}"


class DeclarationItem(models.Model):
    """Beyan içindeki malzeme/cihaz satırları"""

    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE, related_name='items')
    line_number = models.IntegerField(default=1)

    # MaterialProduct ile ilişki (opsiyonel - manuel veya seçimle)
    material_product = models.ForeignKey('MaterialProduct', on_delete=models.SET_NULL, null=True, blank=True)

    # Zahntec formatına uygun field'lar
    material = models.CharField(max_length=200, verbose_name="Material", help_text="Malzeme adı")
    firma = models.CharField(max_length=200, verbose_name="Hersteller", help_text="Üretici firma")
    bestandteile = models.CharField(max_length=500, verbose_name="Bestandteile", help_text="İçerik/Bileşenler")
    material_lot_no = models.CharField(max_length=100, verbose_name="Material Lot No.", help_text="Lot numarası")
    ce_status = models.CharField(max_length=10, default="Ja", verbose_name="CE", help_text="CE durumu")

    # Eski field'ları koruyoruz (backward compatibility için)
    device_identification = models.CharField(max_length=200, blank=True, verbose_name="Produkt", help_text="Ürün tanımı")

    class Meta:
        ordering = ['line_number']
        verbose_name = 'Beyan Satırı'
        verbose_name_plural = 'Beyan Satırları'

    def __str__(self):
        return f"{self.line_number}. {self.material} - {self.firma}"


class MaterialProduct(models.Model):
    """Hazır malzeme ürün kombinasyonları (Zahntec labor_products gibi)"""

    name = models.CharField(max_length=200, help_text="Ürün kombinasyon adı", unique=True)

    # Yeni Zahntec formatı
    material = models.CharField(max_length=200, verbose_name="Material", help_text="Malzeme")
    firma = models.CharField(max_length=200, verbose_name="Hersteller", help_text="Üretici firma")
    bestandteile = models.CharField(max_length=500, verbose_name="Bestandteile", help_text="İçerik/Bileşenler")
    material_lot_no = models.CharField(max_length=100, verbose_name="Material Lot No.", help_text="Lot numarası")
    ce_status = models.CharField(max_length=10, default="Ja", verbose_name="CE", help_text="CE durumu")

    # Ek bilgi
    device_identification = models.CharField(max_length=200, blank=True, verbose_name="Produkt", help_text="Ürün tanımı")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Material Product'
        verbose_name_plural = 'Material Products'

    def __str__(self):
        return f"{self.name} ({self.material})"
