"""Factura-e B2B forms."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import FacturaeBBSettings


class FacturaeBBSettingsForm(forms.ModelForm):
    class Meta:
        model = FacturaeBBSettings
        fields = [
            'company_name', 'tax_id',
            'address_street', 'address_city', 'address_postal_code',
            'address_province', 'country_code',
            'customization_id', 'profile_id',
            'auto_generate', 'auto_sign',
            'currency_code',
        ]


class CertificateUploadForm(forms.Form):
    certificate = forms.FileField(
        label=_('Certificate (.p12)'),
        widget=forms.FileInput(attrs={'class': 'input', 'accept': '.p12,.pfx'}),
    )
    password = forms.CharField(
        label=_('Certificate Password'),
        widget=forms.PasswordInput(attrs={'class': 'input'}),
        required=False,
    )
