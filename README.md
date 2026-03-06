# Factura-e B2B Module

EN 16931 compliant electronic invoicing in UBL 2.1 format for ERPlora Hub.

## Features

- Generate UBL 2.1 XML e-invoices from existing invoices
- Digital signature with PKCS#12 certificates (.p12)
- Full lifecycle: Draft > Generated > Signed > Sent > Accepted/Rejected
- Bulk generation from multiple invoices
- Dashboard with status overview and pending actions
- Audit log for all e-invoice operations
- Auto-generate and auto-sign options
- Download XML and signed XML files

## Installation

This module is installed automatically via the ERPlora Marketplace.

**Dependencies**: Requires `invoicing` module.

## Configuration

Access settings via: **Menu > Factura-e B2B > Settings**

Settings include:
- Company data (name, NIF/CIF, address, country code)
- Certificate upload (.p12) and password
- UBL customization ID and profile ID (PEPPOL defaults)
- Auto-generate and auto-sign toggles
- Currency code

## Usage

Access via: **Menu > Factura-e B2B**

### Views

| View | URL | Description |
|------|-----|-------------|
| Dashboard | `/m/facturae_b2b/` | Status overview, pending actions, certificate validity |
| E-Invoices | `/m/facturae_b2b/einvoices/` | List all e-invoices with status filters |
| E-Invoice Detail | `/m/facturae_b2b/einvoices/<id>/` | Detail view of a single e-invoice |
| Generate Select | `/m/facturae_b2b/generate/` | Select invoices for e-invoice generation |
| Settings | `/m/facturae_b2b/settings/` | Module configuration |

### Actions

| Action | URL | Method |
|--------|-----|--------|
| Generate from Invoice | `/m/facturae_b2b/generate/<invoice_id>/` | POST |
| Bulk Generate | `/m/facturae_b2b/generate/bulk/` | POST |
| Sign E-Invoice | `/m/facturae_b2b/einvoices/<id>/sign/` | POST |
| Download XML | `/m/facturae_b2b/einvoices/<id>/download/` | GET |
| Download Signed XML | `/m/facturae_b2b/einvoices/<id>/download-signed/` | GET |
| Regenerate | `/m/facturae_b2b/einvoices/<id>/regenerate/` | POST |
| Delete | `/m/facturae_b2b/einvoices/<id>/delete/` | POST |
| Bulk Actions | `/m/facturae_b2b/einvoices/bulk/` | POST |
| Save Settings | `/m/facturae_b2b/settings/save/` | POST |
| Upload Certificate | `/m/facturae_b2b/settings/certificate/` | POST |
| Remove Certificate | `/m/facturae_b2b/settings/certificate/remove/` | POST |

### Compliance

- EN 16931 (European e-invoicing standard)
- PEPPOL BIS Billing 3.0
- UBL 2.1 XML format

## Models

| Model | Description |
|-------|-------------|
| `FacturaeBBSettings` | Per-hub settings (company data, certificate, UBL defaults, auto-generate/sign) |
| `EInvoice` | Electronic invoice document with UBL XML, signed XML, status lifecycle, and AEAT response |
| `EInvoiceLog` | Audit trail for e-invoice actions (generated, signed, sent, accepted, rejected, error) |

## Permissions

| Permission | Description |
|------------|-------------|
| `facturae_b2b.view_einvoice` | View e-invoices |
| `facturae_b2b.generate_einvoice` | Generate e-invoices |
| `facturae_b2b.sign_einvoice` | Sign e-invoices |
| `facturae_b2b.send_einvoice` | Send e-invoices |
| `facturae_b2b.manage_settings` | Manage settings |

## Integration with Other Modules

| Module | Integration |
|--------|-------------|
| `invoicing` | E-invoices are generated from Invoice records (OneToOne FK) |

## Dependencies

- `invoicing` module

## License

MIT

## Author

ERPlora Team - support@erplora.com
