"""Factura-e B2B views."""

from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render as django_render
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils.translation import gettext as _
from django.utils import timezone

from apps.accounts.decorators import login_required, permission_required
from apps.core.htmx import htmx_view
from apps.modules_runtime.navigation import with_module_nav

from .models import FacturaeBBSettings, EInvoice, EInvoiceLog
from .ubl import generate_ubl_xml, validate_ubl_xml
from .signing import load_p12_certificate, sign_xml
from .forms import CertificateUploadForm

SORT_FIELDS = {
    'invoice': 'invoice__number',
    'status': 'status',
    'created': 'created_at',
    'customer': 'invoice__customer_name',
}

GENERATE_SORT_FIELDS = {
    'number': 'number',
    'customer': 'customer_name',
    'date': 'issue_date',
    'total': 'total_amount',
    'status': 'status',
}


def _hub(request):
    return request.session.get('hub_id')


# -----------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------

@login_required
@permission_required('facturae_b2b.view_einvoice')
@with_module_nav('facturae_b2b', 'dashboard')
@htmx_view('facturae_b2b/pages/dashboard.html', 'facturae_b2b/partials/dashboard_content.html')
def index(request):
    hub = _hub(request)
    qs = EInvoice.objects.filter(hub_id=hub, is_deleted=False)

    generated_count = qs.filter(status='generated').count()
    signed_count = qs.filter(status='signed').count()
    sent_count = qs.filter(status='sent').count()
    accepted_count = qs.filter(status='accepted').count()
    rejected_count = qs.filter(status='rejected').count()
    error_count = qs.filter(status='error').count()
    total_count = qs.count()

    from invoicing.models import Invoice
    eligible_count = Invoice.objects.filter(
        hub_id=hub, is_deleted=False,
        status__in=['issued', 'paid'],
    ).exclude(einvoice__isnull=False).count()

    recent = qs.select_related('invoice').order_by('-created_at')[:10]
    settings_obj = FacturaeBBSettings.get_settings(hub)

    return {
        'generated_count': generated_count,
        'signed_count': signed_count,
        'sent_count': sent_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'error_count': error_count,
        'total_count': total_count,
        'eligible_count': eligible_count,
        'recent_einvoices': recent,
        'has_certificate': settings_obj.has_certificate,
        'certificate_valid': settings_obj.certificate_valid,
    }


# -----------------------------------------------------------------------
# E-Invoices List
# -----------------------------------------------------------------------

def _einvoices_ctx(request):
    """Build einvoices list context (shared between list view and bulk action)."""
    hub = _hub(request)
    params = request.GET if request.method == 'GET' else request.POST
    qs = EInvoice.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('invoice')

    search = params.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(ubl_invoice_id__icontains=search) |
            Q(invoice__number__icontains=search) |
            Q(invoice__customer_name__icontains=search)
        )

    status_filter = params.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    sort_field = params.get('sort', 'created')
    sort_dir = params.get('dir', 'desc')
    order_by = SORT_FIELDS.get(sort_field, 'created_at')
    if sort_dir == 'desc':
        order_by = f'-{order_by}'
    qs = qs.order_by(order_by)

    per_page = int(params.get('per_page', 10))
    if per_page not in (10, 25, 50, 100):
        per_page = 10
    page_obj = Paginator(qs, per_page).get_page(params.get('page', 1))

    current_view = params.get('view', 'table')
    if current_view not in ('table', 'cards'):
        current_view = 'table'

    return {
        'einvoices': page_obj,
        'page_obj': page_obj,
        'search': search,
        'sort_field': sort_field,
        'sort_dir': sort_dir,
        'status_filter': status_filter,
        'per_page': per_page,
        'current_view': current_view,
        'status_choices': EInvoice.Status.choices,
    }


@login_required
@permission_required('facturae_b2b.view_einvoice')
@with_module_nav('facturae_b2b', 'einvoices')
@htmx_view('facturae_b2b/pages/einvoices.html', 'facturae_b2b/partials/einvoices_content.html')
def einvoices_list(request):
    ctx = _einvoices_ctx(request)

    if getattr(request, 'htmx', None) and getattr(request.htmx, 'target', '') == 'datatable-body':
        return django_render(request, 'facturae_b2b/partials/einvoices_table.html', ctx)

    return ctx


# -----------------------------------------------------------------------
# E-Invoice Detail
# -----------------------------------------------------------------------

@login_required
@permission_required('facturae_b2b.view_einvoice')
@with_module_nav('facturae_b2b', 'einvoices')
@htmx_view('facturae_b2b/pages/einvoice_detail.html', 'facturae_b2b/partials/einvoice_detail_content.html')
def einvoice_detail(request, pk):
    hub = _hub(request)
    einvoice = EInvoice.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).select_related('invoice', 'invoice__series').first()

    if not einvoice:
        return {'error': _('E-Invoice not found')}

    logs = EInvoiceLog.objects.filter(
        einvoice=einvoice, is_deleted=False,
    ).order_by('-created_at')[:20]

    settings_obj = FacturaeBBSettings.get_settings(hub)

    return {
        'einvoice': einvoice,
        'logs': logs,
        'has_certificate': settings_obj.has_certificate,
    }


# -----------------------------------------------------------------------
# Generate
# -----------------------------------------------------------------------

def _generate_ctx(request):
    """Build generate invoices list context."""
    hub = _hub(request)
    from invoicing.models import Invoice

    params = request.GET if request.method == 'GET' else request.POST

    eligible = Invoice.objects.filter(
        hub_id=hub, is_deleted=False,
        status__in=['issued', 'paid'],
    ).exclude(einvoice__isnull=False)

    search = params.get('q', '').strip()
    if search:
        eligible = eligible.filter(
            Q(number__icontains=search) |
            Q(customer_name__icontains=search)
        )

    status_filter = params.get('status', '').strip()
    if status_filter in ('issued', 'paid'):
        eligible = eligible.filter(status=status_filter)

    sort_field = params.get('sort', 'date')
    sort_dir = params.get('dir', 'desc')
    db_field = GENERATE_SORT_FIELDS.get(sort_field, 'issue_date')
    if sort_dir == 'desc':
        db_field = f'-{db_field}'
    eligible = eligible.order_by(db_field)

    per_page = min(int(params.get('per_page', 25)), 100)
    page_obj = Paginator(eligible, per_page).get_page(params.get('page', 1))

    return {
        'invoices': page_obj,
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'sort_field': sort_field,
        'sort_dir': sort_dir,
        'per_page': per_page,
    }


@login_required
@permission_required('facturae_b2b.generate_einvoice')
@with_module_nav('facturae_b2b', 'einvoices')
@htmx_view('facturae_b2b/pages/generate.html', 'facturae_b2b/partials/generate_content.html')
def generate_select(request):
    return _generate_ctx(request)


@login_required
@permission_required('facturae_b2b.generate_einvoice')
@require_POST
def generate_from_invoice(request, invoice_pk):
    hub = _hub(request)
    from invoicing.models import Invoice

    invoice = Invoice.objects.filter(
        pk=invoice_pk, hub_id=hub, is_deleted=False,
        status__in=['issued', 'paid'],
    ).first()

    if not invoice:
        return JsonResponse({'ok': False, 'error': _('Invoice not found or not eligible')}, status=400)

    if hasattr(invoice, 'einvoice') and EInvoice.objects.filter(invoice=invoice).exists():
        return JsonResponse({'ok': False, 'error': _('E-Invoice already exists for this invoice')}, status=400)

    settings_obj = FacturaeBBSettings.get_settings(hub)

    if not settings_obj.company_name or not settings_obj.tax_id:
        return JsonResponse({
            'ok': False,
            'error': _('Company name and Tax ID must be configured in settings'),
        }, status=400)

    try:
        xml_string, ubl_id = generate_ubl_xml(invoice, settings_obj)

        is_valid, errors = validate_ubl_xml(xml_string)
        if not is_valid:
            return JsonResponse({
                'ok': False,
                'error': _('Generated XML failed validation: ') + '; '.join(errors),
            }, status=400)

        einvoice = EInvoice.objects.create(
            hub_id=hub,
            invoice=invoice,
            status=EInvoice.Status.GENERATED,
            ubl_invoice_id=ubl_id,
            xml_content=xml_string,
        )

        filename = f'{ubl_id}.xml'
        einvoice.xml_file.save(filename, ContentFile(xml_string.encode('utf-8')), save=True)

        EInvoiceLog.objects.create(
            hub_id=hub,
            einvoice=einvoice,
            action=EInvoiceLog.Action.GENERATED,
            details=_('UBL 2.1 XML generated successfully'),
        )

        # Auto-sign if configured
        if settings_obj.auto_sign and settings_obj.has_certificate and settings_obj.certificate_valid:
            try:
                _do_sign(einvoice, settings_obj, hub)
            except Exception as e:
                EInvoiceLog.objects.create(
                    hub_id=hub,
                    einvoice=einvoice,
                    action=EInvoiceLog.Action.ERROR,
                    details=f'Auto-sign failed: {e}',
                )

        return JsonResponse({'ok': True, 'id': str(einvoice.pk)})

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@permission_required('facturae_b2b.generate_einvoice')
@require_POST
def generate_bulk(request):
    hub = _hub(request)
    invoice_ids = [i.strip() for i in request.POST.get('ids', '').split(',') if i.strip()]

    if not invoice_ids:
        return JsonResponse({'ok': False, 'error': _('No invoices selected')}, status=400)

    settings_obj = FacturaeBBSettings.get_settings(hub)
    if not settings_obj.company_name or not settings_obj.tax_id:
        return JsonResponse({
            'ok': False,
            'error': _('Company name and Tax ID must be configured in settings'),
        }, status=400)

    from invoicing.models import Invoice
    success_count = 0
    error_count = 0

    for inv_id in invoice_ids:
        invoice = Invoice.objects.filter(
            pk=inv_id, hub_id=hub, is_deleted=False,
            status__in=['issued', 'paid'],
        ).first()

        if not invoice or EInvoice.objects.filter(invoice=invoice).exists():
            error_count += 1
            continue

        try:
            xml_string, ubl_id = generate_ubl_xml(invoice, settings_obj)
            einvoice = EInvoice.objects.create(
                hub_id=hub, invoice=invoice,
                status=EInvoice.Status.GENERATED,
                ubl_invoice_id=ubl_id, xml_content=xml_string,
            )
            einvoice.xml_file.save(
                f'{ubl_id}.xml',
                ContentFile(xml_string.encode('utf-8')),
                save=True,
            )
            EInvoiceLog.objects.create(
                hub_id=hub, einvoice=einvoice,
                action=EInvoiceLog.Action.GENERATED,
                details=_('Bulk generation'),
            )

            if settings_obj.auto_sign and settings_obj.has_certificate and settings_obj.certificate_valid:
                try:
                    _do_sign(einvoice, settings_obj, hub)
                except Exception:
                    pass

            success_count += 1
        except Exception:
            error_count += 1

    return JsonResponse({
        'ok': True,
        'generated': success_count,
        'errors': error_count,
    })


# -----------------------------------------------------------------------
# Sign
# -----------------------------------------------------------------------

def _do_sign(einvoice, settings_obj, hub):
    """Sign an e-invoice with the configured certificate."""
    settings_obj.certificate_file.open('rb')
    p12_data = settings_obj.certificate_file.read()
    settings_obj.certificate_file.close()

    private_key_pem, cert_pem, cert_info = load_p12_certificate(
        p12_data, settings_obj.certificate_password,
    )

    signed_xml = sign_xml(einvoice.xml_content, private_key_pem, cert_pem)

    filename = f'{einvoice.ubl_invoice_id}_signed.xml'
    einvoice.signed_xml_file.save(
        filename, ContentFile(signed_xml.encode('utf-8')), save=False,
    )
    einvoice.status = EInvoice.Status.SIGNED
    einvoice.signature_timestamp = timezone.now()
    einvoice.save(update_fields=[
        'signed_xml_file', 'status', 'signature_timestamp', 'updated_at',
    ])

    EInvoiceLog.objects.create(
        hub_id=hub,
        einvoice=einvoice,
        action=EInvoiceLog.Action.SIGNED,
        details=_('Signed with certificate: ') + cert_info.get('subject', ''),
    )


@login_required
@permission_required('facturae_b2b.sign_einvoice')
@require_POST
def einvoice_sign(request, pk):
    hub = _hub(request)
    einvoice = EInvoice.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
        status__in=['generated', 'error'],
    ).first()

    if not einvoice:
        return JsonResponse({'ok': False, 'error': _('E-Invoice not found or not eligible for signing')}, status=400)

    settings_obj = FacturaeBBSettings.get_settings(hub)

    if not settings_obj.has_certificate:
        return JsonResponse({'ok': False, 'error': _('No certificate configured')}, status=400)

    if not settings_obj.certificate_valid:
        return JsonResponse({'ok': False, 'error': _('Certificate has expired')}, status=400)

    try:
        _do_sign(einvoice, settings_obj, hub)
        return JsonResponse({'ok': True})
    except Exception as e:
        einvoice.status = EInvoice.Status.ERROR
        einvoice.error_message = str(e)
        einvoice.save(update_fields=['status', 'error_message', 'updated_at'])
        EInvoiceLog.objects.create(
            hub_id=hub, einvoice=einvoice,
            action=EInvoiceLog.Action.ERROR,
            details=f'Signing failed: {e}',
        )
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# -----------------------------------------------------------------------
# Download
# -----------------------------------------------------------------------

@login_required
@permission_required('facturae_b2b.view_einvoice')
def einvoice_download(request, pk):
    hub = _hub(request)
    einvoice = EInvoice.objects.filter(pk=pk, hub_id=hub, is_deleted=False).first()

    if not einvoice or not einvoice.xml_content:
        return HttpResponse(_('E-Invoice not found'), status=404)

    EInvoiceLog.objects.create(
        hub_id=hub, einvoice=einvoice,
        action=EInvoiceLog.Action.DOWNLOADED,
        details=_('XML downloaded'),
    )

    response = HttpResponse(einvoice.xml_content, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="{einvoice.ubl_invoice_id}.xml"'
    return response


@login_required
@permission_required('facturae_b2b.view_einvoice')
def einvoice_download_signed(request, pk):
    hub = _hub(request)
    einvoice = EInvoice.objects.filter(pk=pk, hub_id=hub, is_deleted=False).first()

    if not einvoice or not einvoice.signed_xml_file:
        return HttpResponse(_('Signed e-invoice not found'), status=404)

    EInvoiceLog.objects.create(
        hub_id=hub, einvoice=einvoice,
        action=EInvoiceLog.Action.DOWNLOADED,
        details=_('Signed XML downloaded'),
    )

    einvoice.signed_xml_file.open('rb')
    content = einvoice.signed_xml_file.read()
    einvoice.signed_xml_file.close()

    response = HttpResponse(content, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="{einvoice.ubl_invoice_id}_signed.xml"'
    return response


# -----------------------------------------------------------------------
# Regenerate / Delete
# -----------------------------------------------------------------------

@login_required
@permission_required('facturae_b2b.generate_einvoice')
@require_POST
def einvoice_regenerate(request, pk):
    hub = _hub(request)
    einvoice = EInvoice.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).select_related('invoice').first()

    if not einvoice:
        return JsonResponse({'ok': False, 'error': _('E-Invoice not found')}, status=404)

    if einvoice.status in ('sent', 'accepted'):
        return JsonResponse({'ok': False, 'error': _('Cannot regenerate a sent/accepted e-invoice')}, status=400)

    settings_obj = FacturaeBBSettings.get_settings(hub)

    try:
        xml_string, ubl_id = generate_ubl_xml(einvoice.invoice, settings_obj)
        einvoice.xml_content = xml_string
        einvoice.ubl_invoice_id = ubl_id
        einvoice.status = EInvoice.Status.GENERATED
        einvoice.error_message = ''
        einvoice.signed_xml_file = None
        einvoice.signature_timestamp = None
        einvoice.xml_file.save(
            f'{ubl_id}.xml',
            ContentFile(xml_string.encode('utf-8')),
            save=False,
        )
        einvoice.save()

        EInvoiceLog.objects.create(
            hub_id=hub, einvoice=einvoice,
            action=EInvoiceLog.Action.REGENERATED,
            details=_('XML regenerated'),
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@permission_required('facturae_b2b.generate_einvoice')
@require_POST
def einvoice_delete(request, pk):
    hub = _hub(request)
    einvoice = EInvoice.objects.filter(pk=pk, hub_id=hub, is_deleted=False).first()

    if not einvoice:
        return JsonResponse({'ok': False}, status=404)

    if einvoice.status in ('sent', 'accepted'):
        return JsonResponse({'ok': False, 'error': _('Cannot delete a sent/accepted e-invoice')}, status=400)

    einvoice.is_deleted = True
    einvoice.deleted_at = timezone.now()
    einvoice.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    return JsonResponse({'ok': True})


@login_required
@permission_required('facturae_b2b.generate_einvoice')
@require_POST
def einvoices_bulk_action(request):
    hub = _hub(request)
    ids = [i.strip() for i in request.POST.get('ids', '').split(',') if i.strip()]
    action = request.POST.get('action', '')

    if action == 'sign':
        settings_obj = FacturaeBBSettings.get_settings(hub)
        if not settings_obj.has_certificate or not settings_obj.certificate_valid:
            return JsonResponse({'ok': False, 'error': _('No valid certificate')}, status=400)

        for eid in ids:
            ei = EInvoice.objects.filter(
                pk=eid, hub_id=hub, is_deleted=False, status='generated',
            ).first()
            if ei:
                try:
                    _do_sign(ei, settings_obj, hub)
                except Exception:
                    pass

    elif action == 'delete':
        EInvoice.objects.filter(
            hub_id=hub, is_deleted=False, id__in=ids,
            status__in=['draft', 'generated', 'error'],
        ).update(is_deleted=True, deleted_at=timezone.now())

    else:
        return JsonResponse({'ok': False, 'error': _('Unknown action')}, status=400)

    # Re-render the table partial
    ctx = _einvoices_ctx(request)
    return django_render(request, 'facturae_b2b/partials/einvoices_table.html', ctx)


# -----------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------

@login_required
@permission_required('facturae_b2b.manage_settings')
@with_module_nav('facturae_b2b', 'settings')
@htmx_view('facturae_b2b/pages/settings.html', 'facturae_b2b/partials/settings_content.html')
def settings_view(request):
    hub = _hub(request)
    settings_obj = FacturaeBBSettings.get_settings(hub)
    return {'settings': settings_obj}


@login_required
@permission_required('facturae_b2b.manage_settings')
@require_POST
def settings_save(request):
    hub = _hub(request)
    settings_obj = FacturaeBBSettings.get_settings(hub)
    from .forms import FacturaeBBSettingsForm
    form = FacturaeBBSettingsForm(request.POST, instance=settings_obj)
    if form.is_valid():
        form.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@permission_required('facturae_b2b.manage_settings')
@require_POST
def settings_toggle(request):
    hub = _hub(request)
    settings_obj = FacturaeBBSettings.get_settings(hub)
    field = request.POST.get('field')
    if field not in ('auto_generate', 'auto_sign'):
        return JsonResponse({'ok': False, 'error': _('Invalid field')}, status=400)

    current = getattr(settings_obj, field)
    setattr(settings_obj, field, not current)
    settings_obj.save(update_fields=[field, 'updated_at'])
    return JsonResponse({'ok': True, 'value': not current})


@login_required
@permission_required('facturae_b2b.manage_settings')
@require_POST
def settings_input(request):
    hub = _hub(request)
    settings_obj = FacturaeBBSettings.get_settings(hub)
    field = request.POST.get('field')
    value = request.POST.get('value', '')
    allowed = {
        'company_name', 'tax_id', 'address_street', 'address_city',
        'address_postal_code', 'address_province', 'country_code',
        'customization_id', 'profile_id', 'currency_code',
    }
    if field not in allowed:
        return JsonResponse({'ok': False, 'error': _('Invalid field')}, status=400)

    setattr(settings_obj, field, value)
    settings_obj.save(update_fields=[field, 'updated_at'])
    return JsonResponse({'ok': True})


@login_required
@permission_required('facturae_b2b.manage_settings')
@require_POST
def settings_certificate_upload(request):
    hub = _hub(request)
    settings_obj = FacturaeBBSettings.get_settings(hub)
    form = CertificateUploadForm(request.POST, request.FILES)

    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    cert_file = form.cleaned_data['certificate']
    password = form.cleaned_data['password']

    try:
        cert_bytes = cert_file.read()
        _, _, cert_info = load_p12_certificate(cert_bytes, password)

        settings_obj.certificate_file.save(
            cert_file.name, ContentFile(cert_bytes), save=False,
        )
        settings_obj.certificate_password = password
        settings_obj.certificate_subject = cert_info.get('subject', '')
        settings_obj.certificate_expiry = cert_info.get('not_after')
        settings_obj.save()

        return JsonResponse({
            'ok': True,
            'subject': cert_info.get('subject', ''),
            'expiry': str(cert_info.get('not_after', '')),
        })
    except ValueError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@permission_required('facturae_b2b.manage_settings')
@require_POST
def settings_certificate_remove(request):
    hub = _hub(request)
    settings_obj = FacturaeBBSettings.get_settings(hub)

    if settings_obj.certificate_file:
        settings_obj.certificate_file.delete(save=False)
    settings_obj.certificate_password = ''
    settings_obj.certificate_subject = ''
    settings_obj.certificate_expiry = None
    settings_obj.save()

    return JsonResponse({'ok': True})
