from django.utils.translation import gettext_lazy as _

MODULE_ID = 'facturae_b2b'
MODULE_NAME = _('Factura-e B2B')
MODULE_VERSION = '1.0.0'
MODULE_ICON = 'code-slash-outline'
MODULE_DESCRIPTION = _('EN 16931 compliant electronic invoicing in UBL 2.1 format')
MODULE_AUTHOR = 'ERPlora'
MODULE_CATEGORY = 'compliance'

MENU = {
    'label': _('Factura-e B2B'),
    'icon': 'code-slash-outline',
    'order': 82,
}

NAVIGATION = [
    {'id': 'dashboard', 'label': _('Dashboard'), 'icon': 'speedometer-outline'},
    {'id': 'einvoices', 'label': _('E-Invoices'), 'icon': 'code-slash-outline'},
    {'id': 'settings', 'label': _('Settings'), 'icon': 'settings-outline'},
]

DEPENDENCIES = ['invoicing']

PERMISSIONS = [
    'facturae_b2b.view_einvoice',
    'facturae_b2b.generate_einvoice',
    'facturae_b2b.sign_einvoice',
    'facturae_b2b.send_einvoice',
    'facturae_b2b.manage_settings',
]
