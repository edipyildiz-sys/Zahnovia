from django import forms
from .models import Declaration, DeclarationItem, ProductWork


class DeclarationForm(forms.ModelForm):
    class Meta:
        model = Declaration
        fields = []  # Sadece praxis otomatik atanacak


class ProductWorkForm(forms.ModelForm):
    class Meta:
        model = ProductWork
        fields = ['produktbezeichnung_arbeit', 'zahnnummer', 'zahnfarbe']
        widgets = {
            'produktbezeichnung_arbeit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. Krone, Brücke'}),
            'zahnnummer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. 11, 21'}),
            'zahnfarbe': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. A2, B1'}),
        }


class DeclarationItemForm(forms.ModelForm):
    class Meta:
        model = DeclarationItem
        fields = ['material', 'firma', 'bestandteile', 'material_lot_no', 'ce_status']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-control material-select'}),
            'firma': forms.Select(attrs={'class': 'form-control firma-select'}),
            'bestandteile': forms.TextInput(attrs={'class': 'form-control bestandteile-input', 'placeholder': 'Bestandteile', 'readonly': 'readonly'}),
            'material_lot_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lot No.'}),
            'ce_status': forms.TextInput(attrs={'class': 'form-control', 'value': 'Ja'}),
        }


# Formset for product works
ProductWorkFormSet = forms.inlineformset_factory(
    Declaration,
    ProductWork,
    form=ProductWorkForm,
    extra=1,
    max_num=20,
    can_delete=True
)

# Formset for multiple items
DeclarationItemFormSet = forms.inlineformset_factory(
    Declaration,
    DeclarationItem,
    form=DeclarationItemForm,
    extra=1,  # Başlangıçta 1 satır
    max_num=20,  # Maksimum 20 satır
    can_delete=True  # Silme butonu olacak
)
