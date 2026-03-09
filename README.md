# Factura-e B2B

## Overview

| Property | Value |
|----------|-------|
| **Module ID** | `facturae_b2b` |
| **Version** | `1.0.0` |
| **Icon** | `code-slash-outline` |
| **Dependencies** | `invoicing` |

## Dependencies

This module requires the following modules to be installed:

- `invoicing`

## Models

### `FacturaeBBSettings`

Per-hub e-invoice settings (singleton via unique hub_id).

| Field | Type | Details |
|-------|------|---------|
| `company_name` | CharField | max_length=255, optional |
| `tax_id` | CharField | max_length=50, optional |
| `address_street` | CharField | max_length=255, optional |
| `address_city` | CharField | max_length=100, optional |
| `address_postal_code` | CharField | max_length=20, optional |
| `address_province` | CharField | max_length=100, optional |
| `country_code` | CharField | max_length=2 |
| `certificate_file` | FileField | max_length=100, optional |
| `certificate_password` | CharField | max_length=255, optional |
| `certificate_subject` | CharField | max_length=500, optional |
| `certificate_expiry` | DateTimeField | optional |
| `customization_id` | CharField | max_length=255 |
| `profile_id` | CharField | max_length=255 |
| `auto_generate` | BooleanField |  |
| `auto_sign` | BooleanField |  |
| `currency_code` | CharField | max_length=3 |

**Methods:**

- `get_settings()`

**Properties:**

- `has_certificate`
- `certificate_valid`

### `EInvoice`

Electronic invoice document (UBL 2.1 XML).

| Field | Type | Details |
|-------|------|---------|
| `invoice` | OneToOneField | → `invoicing.Invoice`, on_delete=CASCADE |
| `status` | CharField | max_length=20, choices: draft, generated, signed, sent, accepted, rejected, ... |
| `ubl_invoice_id` | CharField | max_length=100, optional |
| `xml_content` | TextField | optional |
| `xml_file` | FileField | max_length=100, optional |
| `signed_xml_file` | FileField | max_length=100, optional |
| `signature_timestamp` | DateTimeField | optional |
| `error_message` | TextField | optional |
| `sent_at` | DateTimeField | optional |
| `accepted_at` | DateTimeField | optional |
| `rejected_at` | DateTimeField | optional |
| `response_code` | CharField | max_length=50, optional |
| `response_message` | TextField | optional |

### `EInvoiceLog`

Audit trail for e-invoice actions.

| Field | Type | Details |
|-------|------|---------|
| `einvoice` | ForeignKey | → `facturae_b2b.EInvoice`, on_delete=CASCADE |
| `action` | CharField | max_length=20, choices: generated, signed, sent, accepted, rejected, error, ... |
| `details` | TextField | optional |

## Cross-Module Relationships

| From | Field | To | on_delete | Nullable |
|------|-------|----|-----------|----------|
| `EInvoice` | `invoice` | `invoicing.Invoice` | CASCADE | No |
| `EInvoiceLog` | `einvoice` | `facturae_b2b.EInvoice` | CASCADE | No |

## URL Endpoints

Base path: `/m/facturae_b2b/`

| Path | Name | Method |
|------|------|--------|
| `(root)` | `dashboard` | GET |
| `einvoices/` | `einvoices` | GET |
| `einvoices/<uuid:pk>/` | `einvoice_detail` | GET |
| `generate/` | `generate_select` | GET |
| `generate/<uuid:invoice_pk>/` | `generate_from_invoice` | GET |
| `generate/bulk/` | `generate_bulk` | GET/POST |
| `einvoices/<uuid:pk>/sign/` | `einvoice_sign` | GET |
| `einvoices/<uuid:pk>/download/` | `einvoice_download` | GET |
| `einvoices/<uuid:pk>/download-signed/` | `einvoice_download_signed` | GET |
| `einvoices/<uuid:pk>/regenerate/` | `einvoice_regenerate` | GET |
| `einvoices/<uuid:pk>/delete/` | `einvoice_delete` | GET/POST |
| `einvoices/bulk/` | `einvoices_bulk_action` | GET/POST |
| `settings/` | `settings` | GET |
| `settings/save/` | `settings_save` | GET/POST |
| `settings/toggle/` | `settings_toggle` | GET |
| `settings/input/` | `settings_input` | GET |
| `settings/certificate/` | `settings_certificate_upload` | GET |
| `settings/certificate/remove/` | `settings_certificate_remove` | GET |

## Permissions

| Permission | Description |
|------------|-------------|
| `facturae_b2b.view_einvoice` | View Einvoice |
| `facturae_b2b.generate_einvoice` | Generate Einvoice |
| `facturae_b2b.sign_einvoice` | Sign Einvoice |
| `facturae_b2b.send_einvoice` | Send Einvoice |
| `facturae_b2b.manage_settings` | Manage Settings |

**Role assignments:**

- **admin**: All permissions
- **manager**: `generate_einvoice`, `send_einvoice`, `sign_einvoice`, `view_einvoice`
- **employee**: `view_einvoice`

## Navigation

| View | Icon | ID | Fullpage |
|------|------|----|----------|
| Dashboard | `speedometer-outline` | `dashboard` | No |
| E-Invoices | `code-slash-outline` | `einvoices` | No |
| Settings | `settings-outline` | `settings` | No |

## AI Tools

Tools available for the AI assistant:

### `list_einvoices`

List B2B electronic invoices (UBL/FacturaE).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | draft, generated, signed, sent, accepted, rejected, error |
| `limit` | integer | No |  |

### `get_einvoice_settings`

Get B2B e-invoicing settings (certificate, auto-generate, etc.).

## File Structure

```
README.md
__init__.py
ai_tools.py
apps.py
forms.py
migrations/
  0001_initial.py
  __init__.py
models.py
module.py
signing.py
templates/
  facturae_b2b/
    pages/
      dashboard.html
      einvoice_detail.html
      einvoices.html
      generate.html
      settings.html
    partials/
      dashboard_content.html
      einvoice_detail_content.html
      einvoices_content.html
      einvoices_table.html
      generate_content.html
      generate_table.html
      settings_content.html
ubl.py
urls.py
views.py
```
