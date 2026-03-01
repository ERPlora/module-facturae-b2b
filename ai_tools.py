"""AI tools for the FacturaE B2B module."""
from assistant.tools import AssistantTool, register_tool


@register_tool
class ListEInvoices(AssistantTool):
    name = "list_einvoices"
    description = "List B2B electronic invoices (UBL/FacturaE)."
    module_id = "facturae_b2b"
    required_permission = "facturae_b2b.view_einvoice"
    parameters = {"type": "object", "properties": {"status": {"type": "string", "description": "draft, generated, signed, sent, accepted, rejected, error"}, "limit": {"type": "integer"}}, "required": [], "additionalProperties": False}

    def execute(self, args, request):
        from facturae_b2b.models import EInvoice
        qs = EInvoice.objects.select_related('invoice').all()
        if args.get('status'):
            qs = qs.filter(status=args['status'])
        limit = args.get('limit', 20)
        return {"einvoices": [{"id": str(e.id), "ubl_invoice_id": e.ubl_invoice_id, "status": e.status, "created_at": e.created_at.isoformat()} for e in qs.order_by('-created_at')[:limit]]}


@register_tool
class GetEInvoiceSettings(AssistantTool):
    name = "get_einvoice_settings"
    description = "Get B2B e-invoicing settings (certificate, auto-generate, etc.)."
    module_id = "facturae_b2b"
    required_permission = "facturae_b2b.view_facturaebb settings"
    parameters = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

    def execute(self, args, request):
        from facturae_b2b.models import FacturaeBBSettings
        s = FacturaeBBSettings.get_solo()
        return {
            "company_name": s.company_name, "tax_id": s.tax_id, "country_code": s.country_code,
            "auto_generate": s.auto_generate, "auto_sign": s.auto_sign, "currency_code": s.currency_code,
            "certificate_expiry": s.certificate_expiry.isoformat() if s.certificate_expiry else None,
        }
