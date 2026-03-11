"""
AI context for the Facturae B2B module.
Loaded into the assistant system prompt when this module's tools are active.
"""

CONTEXT = """
## Module Knowledge: Facturae B2B

### Overview
Handles UBL 2.1 electronic invoicing (EN 16931 / PEPPOL BIS Billing 3.0) for B2B
electronic invoice exchange. Each invoicing.Invoice gets a corresponding EInvoice
with signed XML. Requires a .p12 digital certificate.

### Models

**FacturaeBBSettings** (singleton per hub)
- Company: `company_name`, `tax_id` (NIF/CIF), `address_street`, `address_city`,
  `address_postal_code`, `address_province`, `country_code` (default `ES`)
- Certificate: `certificate_file` (.p12 upload), `certificate_password`,
  `certificate_subject`, `certificate_expiry`
- UBL identifiers: `customization_id`, `profile_id` (PEPPOL defaults pre-filled)
- Behavior: `auto_generate` (bool), `auto_sign` (bool)
- `currency_code` (default `EUR`)
- Properties: `has_certificate`, `certificate_valid`
- Access via `FacturaeBBSettings.get_settings(hub_id)`

**EInvoice**
- `invoice` (OneToOne → invoicing.Invoice, related_name `einvoice`)
- `status`: `draft` → `generated` → `signed` → `sent` → `accepted` | `rejected` | `error`
- UBL content: `ubl_invoice_id`, `xml_content` (TextField), `xml_file` (FileField)
- Signed version: `signed_xml_file` (FileField), `signature_timestamp`
- Transmission: `sent_at`, `accepted_at`, `rejected_at`, `response_code`, `response_message`
- `error_message` (TextField): for debugging failures

**EInvoiceLog** (audit trail)
- `einvoice` (FK EInvoice, related_name `logs`)
- `action`: `generated`, `signed`, `sent`, `accepted`, `rejected`, `error`, `downloaded`, `regenerated`
- `details` (TextField): free-text details about the action

### Key flows

**Generate and send a B2B e-invoice:**
1. Ensure `FacturaeBBSettings` has company data and a valid certificate
2. Create `EInvoice` linked to an `invoicing.Invoice` in `draft`
3. Generate UBL 2.1 XML → status `generated`, xml_content populated
4. Sign with .p12 certificate → status `signed`, signed_xml_file saved
5. Send to recipient — status `sent`, `sent_at` recorded
6. Await response → `accepted` (with CSV) or `rejected` (with response_code)
7. Each step creates an `EInvoiceLog` entry

**Check certificate validity:**
- `settings.has_certificate` → True if file uploaded
- `settings.certificate_valid` → True if expiry is in the future

### Relationships
- EInvoice → invoicing.Invoice (OneToOne)
- EInvoiceLog → EInvoice (FK, related_name `logs`)
- Only one EInvoice per Invoice (OneToOne constraint)
"""
