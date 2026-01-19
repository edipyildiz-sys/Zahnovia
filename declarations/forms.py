from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Declaration, DeclarationItem, ProductWork, MaterialProduct, HerstellerProfile


class DeclarationForm(forms.ModelForm):
    class Meta:
        model = Declaration
        fields = []  # Sadece praxis otomatik atanacak


class ProductWorkForm(forms.ModelForm):
    class Meta:
        model = ProductWork
        fields = ['produktbezeichnung_arbeit', 'zahnnummer', 'zahnfarbe']
        widgets = {
            'produktbezeichnung_arbeit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. Krone, Brücke', 'required': 'required'}),
            'zahnnummer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. 11, 21'}),
            'zahnfarbe': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. A2, B1', 'required': 'required'}),
        }


class DeclarationItemForm(forms.ModelForm):
    # Custom field for MaterialProduct selection
    material_product = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label="--- Produkt Wahlen ---",
        widget=forms.Select(attrs={'class': 'form-control material-product-select'})
    )

    class Meta:
        model = DeclarationItem
        fields = ['material', 'firma', 'bestandteile', 'material_lot_no', 'ce_status']
        widgets = {
            'material': forms.TextInput(attrs={'class': 'form-control material-input', 'style': 'display:none;'}),
            'firma': forms.TextInput(attrs={'class': 'form-control firma-input', 'style': 'display:none;'}),
            'bestandteile': forms.TextInput(attrs={'class': 'form-control bestandteile-input', 'placeholder': 'Bestandteile'}),
            'material_lot_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lot No.', 'required': 'required'}),
            'ce_status': forms.TextInput(attrs={'class': 'form-control', 'value': 'Ja'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['material_product'].queryset = MaterialProduct.objects.filter(user=user, is_active=True)


# Formset for product works
ProductWorkFormSet = forms.inlineformset_factory(
    Declaration,
    ProductWork,
    form=ProductWorkForm,
    extra=1,
    max_num=20,
    can_delete=True
)

# Base Formset class to pass user to each form
class BaseDeclarationItemFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['user'] = self.user
        return super()._construct_form(i, **kwargs)

# Formset for multiple items
DeclarationItemFormSet = forms.inlineformset_factory(
    Declaration,
    DeclarationItem,
    form=DeclarationItemForm,
    formset=BaseDeclarationItemFormSet,
    extra=1,  # Başlangıçta 1 satır
    max_num=20,  # Maksimum 20 satır
    can_delete=True  # Silme butonu olacak
)


# ============== KAYIT FORMLARI ==============

class RegistrationForm(forms.Form):
    """Kullanıcı kayıt formu"""

    # Kullanıcı bilgileri
    username = forms.CharField(
        max_length=150,
        label="Benutzername",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Benutzername',
            'autocomplete': 'username'
        })
    )

    email = forms.EmailField(
        label="E-Mail",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ihre@email.de',
            'autocomplete': 'email'
        })
    )

    first_name = forms.CharField(
        max_length=150,
        label="Vorname",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Vorname',
            'autocomplete': 'given-name'
        })
    )

    last_name = forms.CharField(
        max_length=150,
        label="Nachname",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nachname',
            'autocomplete': 'family-name'
        })
    )

    # Şifre
    password = forms.CharField(
        min_length=8,
        label="Passwort",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mindestens 8 Zeichen',
            'autocomplete': 'new-password'
        })
    )

    password_confirm = forms.CharField(
        min_length=8,
        label="Passwort bestätigen",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Passwort wiederholen',
            'autocomplete': 'new-password'
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Dieser Benutzername ist bereits vergeben.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Diese E-Mail-Adresse ist bereits registriert.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        # Django şifre doğrulama
        try:
            validate_password(password)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Die Passwörter stimmen nicht überein.')

        return cleaned_data


class PasswordResetRequestForm(forms.Form):
    """Şifre sıfırlama istek formu"""

    email = forms.EmailField(
        label="E-Mail",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ihre registrierte E-Mail-Adresse',
            'autocomplete': 'email'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('Es gibt kein Konto mit dieser E-Mail-Adresse.')
        return email


class PasswordResetConfirmForm(forms.Form):
    """Yeni şifre belirleme formu"""

    password = forms.CharField(
        min_length=8,
        label="Neues Passwort",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mindestens 8 Zeichen',
            'autocomplete': 'new-password'
        })
    )

    password_confirm = forms.CharField(
        min_length=8,
        label="Passwort bestätigen",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Passwort wiederholen',
            'autocomplete': 'new-password'
        })
    )

    def clean_password(self):
        password = self.cleaned_data.get('password')
        try:
            validate_password(password)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Die Passwörter stimmen nicht überein.')

        return cleaned_data


class HerstellerProfileForm(forms.ModelForm):
    """Profil düzenleme formu"""

    class Meta:
        model = HerstellerProfile
        fields = ['firma_name', 'strasse', 'plz', 'ort', 'telefon', 'verordnender_arzt']
        widgets = {
            'firma_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Firmenname',
                'required': 'required'
            }),
            'strasse': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Straße und Hausnummer',
                'required': 'required'
            }),
            'plz': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'PLZ',
                'required': 'required'
            }),
            'ort': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ort',
                'required': 'required'
            }),
            'telefon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Telefonnummer',
                'required': 'required'
            }),
            'verordnender_arzt': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name des verordnenden Arztes',
                'required': 'required'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        required_fields = ['firma_name', 'strasse', 'plz', 'ort', 'telefon', 'verordnender_arzt']

        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, 'Dieses Feld ist erforderlich.')

        return cleaned_data
