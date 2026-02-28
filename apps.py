from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FacturaeB2BConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facturae_b2b'
    label = 'facturae_b2b'
    verbose_name = _('Factura-e B2B')

    def ready(self):
        pass
