"""Factura-e B2B models — EN 16931 electronic invoicing."""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.core.models import HubBaseModel


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class FacturaeBBSettings(HubBaseModel):
    """Per-hub e-invoice settings (singleton via unique hub_id)."""

    # Company data for e-invoice
    company_name = models.CharField(
        _('Company Name'), max_length=255, blank=True,
    )
    tax_id = models.CharField(
        _('Tax ID (NIF/CIF)'), max_length=50, blank=True,
    )
    address_street = models.CharField(
        _('Street'), max_length=255, blank=True,
    )
    address_city = models.CharField(
        _('City'), max_length=100, blank=True,
    )
    address_postal_code = models.CharField(
        _('Postal Code'), max_length=20, blank=True,
    )
    address_province = models.CharField(
        _('Province'), max_length=100, blank=True,
    )
    country_code = models.CharField(
        _('Country Code'), max_length=2, default='ES',
        help_text=_('ISO 3166-1 alpha-2 code'),
    )

    # Certificate for digital signature
    certificate_file = models.FileField(
        _('Certificate (.p12)'),
        upload_to='facturae_b2b/certificates/',
        blank=True, null=True,
    )
    certificate_password = models.CharField(
        _('Certificate Password'), max_length=255, blank=True,
    )
    certificate_subject = models.CharField(
        _('Certificate Subject'), max_length=500, blank=True,
    )
    certificate_expiry = models.DateTimeField(
        _('Certificate Expiry'), null=True, blank=True,
    )

    # UBL defaults
    customization_id = models.CharField(
        _('Customization ID'), max_length=255,
        default='urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
    )
    profile_id = models.CharField(
        _('Profile ID'), max_length=255,
        default='urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
    )

    # Behavior
    auto_generate = models.BooleanField(
        _('Auto-generate E-Invoice'), default=False,
    )
    auto_sign = models.BooleanField(
        _('Auto-sign E-Invoice'), default=False,
    )

    # Currency
    currency_code = models.CharField(
        _('Currency Code'), max_length=3, default='EUR',
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'facturae_b2b_settings'
        verbose_name = _('E-Invoice Settings')
        verbose_name_plural = _('E-Invoice Settings')
        unique_together = [('hub_id',)]

    def __str__(self):
        return f'E-Invoice Settings (hub={self.hub_id})'

    @classmethod
    def get_settings(cls, hub_id=None):
        if not hub_id:
            from apps.configuration.models import HubConfig
            hub_id = HubConfig.get_solo().hub_id
        obj, _ = cls.all_objects.get_or_create(hub_id=hub_id)
        return obj

    @property
    def has_certificate(self):
        return bool(self.certificate_file)

    @property
    def certificate_valid(self):
        if not self.certificate_expiry:
            return False
        return self.certificate_expiry > timezone.now()


# ---------------------------------------------------------------------------
# E-Invoice
# ---------------------------------------------------------------------------

class EInvoice(HubBaseModel):
    """Electronic invoice document (UBL 2.1 XML)."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        GENERATED = 'generated', _('Generated')
        SIGNED = 'signed', _('Signed')
        SENT = 'sent', _('Sent')
        ACCEPTED = 'accepted', _('Accepted')
        REJECTED = 'rejected', _('Rejected')
        ERROR = 'error', _('Error')

    invoice = models.OneToOneField(
        'invoicing.Invoice',
        on_delete=models.CASCADE,
        related_name='einvoice',
        verbose_name=_('Invoice'),
    )

    status = models.CharField(
        _('Status'), max_length=20,
        choices=Status.choices, default=Status.DRAFT,
    )

    # UBL document
    ubl_invoice_id = models.CharField(
        _('UBL Invoice ID'), max_length=100, blank=True,
    )
    xml_content = models.TextField(
        _('XML Content'), blank=True,
    )
    xml_file = models.FileField(
        _('XML File'),
        upload_to='facturae_b2b/xml/',
        blank=True, null=True,
    )

    # Signed version
    signed_xml_file = models.FileField(
        _('Signed XML File'),
        upload_to='facturae_b2b/signed/',
        blank=True, null=True,
    )
    signature_timestamp = models.DateTimeField(
        _('Signature Timestamp'), null=True, blank=True,
    )

    # Error handling
    error_message = models.TextField(
        _('Error Message'), blank=True,
    )

    # Transmission tracking
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    accepted_at = models.DateTimeField(_('Accepted At'), null=True, blank=True)
    rejected_at = models.DateTimeField(_('Rejected At'), null=True, blank=True)
    response_code = models.CharField(
        _('Response Code'), max_length=50, blank=True,
    )
    response_message = models.TextField(
        _('Response Message'), blank=True,
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'facturae_b2b_einvoice'
        verbose_name = _('E-Invoice')
        verbose_name_plural = _('E-Invoices')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hub_id', 'status']),
            models.Index(fields=['hub_id', 'ubl_invoice_id']),
        ]

    def __str__(self):
        return f'{self.ubl_invoice_id or "Draft"} ({self.get_status_display()})'


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class EInvoiceLog(HubBaseModel):
    """Audit trail for e-invoice actions."""

    class Action(models.TextChoices):
        GENERATED = 'generated', _('Generated')
        SIGNED = 'signed', _('Signed')
        SENT = 'sent', _('Sent')
        ACCEPTED = 'accepted', _('Accepted')
        REJECTED = 'rejected', _('Rejected')
        ERROR = 'error', _('Error')
        DOWNLOADED = 'downloaded', _('Downloaded')
        REGENERATED = 'regenerated', _('Regenerated')

    einvoice = models.ForeignKey(
        EInvoice, on_delete=models.CASCADE,
        related_name='logs', verbose_name=_('E-Invoice'),
    )
    action = models.CharField(
        _('Action'), max_length=20,
        choices=Action.choices,
    )
    details = models.TextField(
        _('Details'), blank=True,
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'facturae_b2b_log'
        verbose_name = _('E-Invoice Log')
        verbose_name_plural = _('E-Invoice Logs')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()} - {self.einvoice}'
