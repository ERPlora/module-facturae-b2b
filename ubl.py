"""
UBL 2.1 XML generation engine — EN 16931 compliant.

Builds a UBL 2.1 Invoice XML document from an invoicing.Invoice instance.
Reference: https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/
"""

from decimal import Decimal

from lxml import etree

# UBL 2.1 Namespaces
NAMESPACES = {
    'ubl': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
}

NSMAP = {
    None: NAMESPACES['ubl'],
    'cac': NAMESPACES['cac'],
    'cbc': NAMESPACES['cbc'],
}


def _el(ns, tag):
    return f'{{{NAMESPACES[ns]}}}{tag}'


def _cbc(tag, text, **attribs):
    el = etree.Element(_el('cbc', tag))
    el.text = str(text) if text is not None else ''
    for k, v in attribs.items():
        el.set(k, str(v))
    return el


def _cac(tag):
    return etree.Element(_el('cac', tag))


def _amount(tag, value, currency='EUR'):
    el = etree.Element(_el('cbc', tag))
    el.text = str(Decimal(str(value)).quantize(Decimal('0.01')))
    el.set('currencyID', currency)
    return el


def _quantity(tag, value, unit_code='EA'):
    el = etree.Element(_el('cbc', tag))
    el.text = str(Decimal(str(value)).quantize(Decimal('0.001')))
    el.set('unitCode', unit_code)
    return el


def _percent(tag, value):
    el = etree.Element(_el('cbc', tag))
    el.text = str(Decimal(str(value)).quantize(Decimal('0.01')))
    return el


def _build_party(name, tax_id, street='', city='', postal_code='',
                 country_code='ES', province=''):
    """Build a cac:Party element (seller or buyer)."""
    party = _cac('Party')

    # PartyName
    party_name = _cac('PartyName')
    party_name.append(_cbc('Name', name))
    party.append(party_name)

    # PostalAddress
    address = _cac('PostalAddress')
    if street:
        address.append(_cbc('StreetName', street))
    if city:
        address.append(_cbc('CityName', city))
    if postal_code:
        address.append(_cbc('PostalZone', postal_code))
    if province:
        address.append(_cbc('CountrySubentity', province))
    country_el = _cac('Country')
    country_el.append(_cbc('IdentificationCode', country_code or 'ES'))
    address.append(country_el)
    party.append(address)

    # PartyTaxScheme
    if tax_id:
        party_tax = _cac('PartyTaxScheme')
        party_tax.append(_cbc('CompanyID', tax_id))
        tax_scheme = _cac('TaxScheme')
        tax_scheme.append(_cbc('ID', 'VAT'))
        party_tax.append(tax_scheme)
        party.append(party_tax)

    # PartyLegalEntity
    legal = _cac('PartyLegalEntity')
    legal.append(_cbc('RegistrationName', name))
    party.append(legal)

    return party


def _map_invoice_type_code(invoice_type):
    """Map internal invoice types to UNTDID 1001 codes."""
    return {
        'invoice': '380',
        'simplified': '380',
        'rectifying': '381',
    }.get(invoice_type, '380')


def _map_payment_means_code(payment_method):
    """Map payment method to UNTDID 4461 code."""
    return {
        'cash': '10',
        'card': '48',
        'credit_card': '48',
        'debit_card': '48',
        'bank_transfer': '30',
        'transfer': '30',
        'check': '20',
        'direct_debit': '49',
    }.get((payment_method or '').lower().replace(' ', '_'), '1')


def generate_ubl_xml(invoice, settings, lines=None):
    """
    Generate a UBL 2.1 XML document from an invoicing.Invoice.

    Args:
        invoice: invoicing.models.Invoice instance (must be issued/paid)
        settings: FacturaeBBSettings instance
        lines: queryset of InvoiceLine (optional)

    Returns:
        tuple: (xml_string, ubl_invoice_id)
    """
    if invoice.status not in ('issued', 'paid'):
        raise ValueError(f'Invoice must be issued or paid, got: {invoice.status}')

    if lines is None:
        lines = invoice.lines.filter(is_deleted=False).order_by('order')

    currency = settings.currency_code or 'EUR'
    ubl_invoice_id = invoice.number

    # Root
    root = etree.Element(_el('ubl', 'Invoice'), nsmap=NSMAP)

    # BT-24: CustomizationID
    root.append(_cbc('CustomizationID', settings.customization_id))
    # BT-23: ProfileID
    root.append(_cbc('ProfileID', settings.profile_id))
    # BT-1: Invoice number
    root.append(_cbc('ID', ubl_invoice_id))
    # BT-2: Issue date
    root.append(_cbc('IssueDate', invoice.issue_date.isoformat()))
    # BT-9: Due date
    if invoice.due_date:
        root.append(_cbc('DueDate', invoice.due_date.isoformat()))
    # BT-3: Invoice type code
    root.append(_cbc('InvoiceTypeCode', _map_invoice_type_code(invoice.invoice_type)))
    # BT-22: Notes
    if invoice.notes:
        root.append(_cbc('Note', invoice.notes))
    # BT-5: Currency
    root.append(_cbc('DocumentCurrencyCode', currency))

    # BG-4: Seller
    supplier = _cac('AccountingSupplierParty')
    supplier.append(_build_party(
        name=settings.company_name,
        tax_id=settings.tax_id,
        street=settings.address_street,
        city=settings.address_city,
        postal_code=settings.address_postal_code,
        country_code=settings.country_code,
        province=settings.address_province,
    ))
    root.append(supplier)

    # BG-7: Buyer
    customer = _cac('AccountingCustomerParty')
    customer.append(_build_party(
        name=invoice.customer_name,
        tax_id=invoice.customer_tax_id,
        street=invoice.customer_address,
        country_code=settings.country_code,
    ))
    root.append(customer)

    # BG-16: Payment means
    if invoice.payment_method:
        payment = _cac('PaymentMeans')
        payment.append(_cbc('PaymentMeansCode',
                            _map_payment_means_code(invoice.payment_method)))
        root.append(payment)

    # BG-23: Tax total
    tax_total = _cac('TaxTotal')
    tax_total.append(_amount('TaxAmount', invoice.tax_amount, currency))

    # Group by tax rate
    tax_rates = {}
    for line in lines:
        rate = line.tax_rate
        if rate not in tax_rates:
            tax_rates[rate] = {'taxable': Decimal('0'), 'tax': Decimal('0')}
        tax_rates[rate]['taxable'] += line.total
        tax_rates[rate]['tax'] += line.total * (rate / Decimal('100'))

    for rate, amounts in tax_rates.items():
        subtotal = _cac('TaxSubtotal')
        subtotal.append(_amount('TaxableAmount', amounts['taxable'], currency))
        subtotal.append(_amount('TaxAmount', amounts['tax'], currency))

        category = _cac('TaxCategory')
        category.append(_cbc('ID', 'S'))
        category.append(_percent('Percent', rate))
        scheme = _cac('TaxScheme')
        scheme.append(_cbc('ID', 'VAT'))
        category.append(scheme)
        subtotal.append(category)
        tax_total.append(subtotal)

    root.append(tax_total)

    # BG-22: Legal monetary totals
    totals = _cac('LegalMonetaryTotal')
    totals.append(_amount('LineExtensionAmount', invoice.subtotal, currency))
    totals.append(_amount('TaxExclusiveAmount', invoice.subtotal, currency))
    totals.append(_amount('TaxInclusiveAmount', invoice.total, currency))
    payable = invoice.total
    if invoice.paid_amount and invoice.paid_amount > 0:
        totals.append(_amount('PrepaidAmount', invoice.paid_amount, currency))
        payable = invoice.total - invoice.paid_amount
    totals.append(_amount('PayableAmount', payable, currency))
    root.append(totals)

    # BG-25: Invoice lines
    for idx, line in enumerate(lines, start=1):
        inv_line = _cac('InvoiceLine')
        inv_line.append(_cbc('ID', str(idx)))
        inv_line.append(_quantity('InvoicedQuantity', line.quantity, 'EA'))
        inv_line.append(_amount('LineExtensionAmount', line.total, currency))

        # Item
        item = _cac('Item')
        item.append(_cbc('Name', line.description))

        if line.product_sku:
            sellers_id = _cac('SellersItemIdentification')
            sellers_id.append(_cbc('ID', line.product_sku))
            item.append(sellers_id)

        # Tax category for line
        line_tax = _cac('ClassifiedTaxCategory')
        line_tax.append(_cbc('ID', 'S'))
        line_tax.append(_percent('Percent', line.tax_rate))
        line_scheme = _cac('TaxScheme')
        line_scheme.append(_cbc('ID', 'VAT'))
        line_tax.append(line_scheme)
        item.append(line_tax)

        inv_line.append(item)

        # Price
        price = _cac('Price')
        price.append(_amount('PriceAmount', line.unit_price, currency))

        if line.discount_percent and line.discount_percent > 0:
            allowance = _cac('AllowanceCharge')
            allowance.append(_cbc('ChargeIndicator', 'false'))
            discount_amount = (
                line.quantity * line.unit_price
                * (line.discount_percent / Decimal('100'))
            )
            allowance.append(_amount('Amount', discount_amount, currency))
            price.append(allowance)

        inv_line.append(price)
        root.append(inv_line)

    # Serialize
    xml_string = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding='UTF-8',
    ).decode('utf-8')

    return xml_string, ubl_invoice_id


def validate_ubl_xml(xml_string):
    """
    Basic structural validation of UBL XML against EN 16931 required fields.

    Returns:
        tuple: (is_valid, errors)
    """
    errors = []
    try:
        root = etree.fromstring(xml_string.encode('utf-8'))

        if not root.tag.endswith('Invoice'):
            errors.append('Root element is not Invoice')

        ns = {'cbc': NAMESPACES['cbc'], 'cac': NAMESPACES['cac']}

        required = [
            ('cbc:ID', 'BT-1 Invoice number'),
            ('cbc:IssueDate', 'BT-2 Issue date'),
            ('cbc:InvoiceTypeCode', 'BT-3 Invoice type code'),
            ('cbc:DocumentCurrencyCode', 'BT-5 Currency code'),
        ]
        for xpath, label in required:
            if root.find(xpath, ns) is None:
                errors.append(f'Missing {label} ({xpath})')

        if root.find('cac:AccountingSupplierParty', ns) is None:
            errors.append('Missing BG-4 Seller')
        if root.find('cac:AccountingCustomerParty', ns) is None:
            errors.append('Missing BG-7 Buyer')
        if not root.findall('cac:InvoiceLine', ns):
            errors.append('Missing BG-25 Invoice lines')
        if root.find('cac:TaxTotal', ns) is None:
            errors.append('Missing BG-23 Tax total')
        if root.find('cac:LegalMonetaryTotal', ns) is None:
            errors.append('Missing BG-22 Legal monetary totals')

    except etree.XMLSyntaxError as e:
        errors.append(f'XML syntax error: {e}')

    return len(errors) == 0, errors
