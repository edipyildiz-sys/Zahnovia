from django import forms
from .models import Declaration, DeclarationItem, ProductWork, MaterialProduct


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
