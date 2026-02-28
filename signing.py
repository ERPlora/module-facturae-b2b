"""
XAdES digital signature for UBL 2.1 XML documents.

Uses signxml + cryptography for .p12 certificate handling.
"""

import logging

from cryptography.hazmat.primitives.serialization import (
    pkcs12, Encoding, PrivateFormat, NoEncryption,
)
from lxml import etree
from signxml import XMLSigner, XMLVerifier, methods

logger = logging.getLogger(__name__)


def load_p12_certificate(file_data, password):
    """
    Load a PKCS#12 (.p12) certificate.

    Args:
        file_data: bytes of the .p12 file
        password: certificate password (string)

    Returns:
        tuple: (private_key_pem, cert_pem, cert_info)
    """
    password_bytes = password.encode('utf-8') if password else None

    try:
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            file_data, password_bytes,
        )
    except Exception as e:
        raise ValueError(f'Failed to load .p12 certificate: {e}')

    if private_key is None:
        raise ValueError('No private key found in .p12 file')
    if certificate is None:
        raise ValueError('No certificate found in .p12 file')

    private_key_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption(),
    )
    cert_pem = certificate.public_bytes(Encoding.PEM)

    cert_info = {
        'subject': certificate.subject.rfc4514_string(),
        'issuer': certificate.issuer.rfc4514_string(),
        'not_before': certificate.not_valid_before_utc,
        'not_after': certificate.not_valid_after_utc,
        'serial_number': str(certificate.serial_number),
    }

    return private_key_pem, cert_pem, cert_info


def sign_xml(xml_string, private_key_pem, cert_pem):
    """
    Apply enveloped XML signature to UBL XML.

    Args:
        xml_string: UBL XML as string
        private_key_pem: PEM-encoded private key bytes
        cert_pem: PEM-encoded certificate bytes

    Returns:
        str: Signed XML as string
    """
    root = etree.fromstring(xml_string.encode('utf-8'))

    signer = XMLSigner(
        method=methods.enveloped,
        digest_algorithm='sha256',
        signature_algorithm='rsa-sha256',
        c14n_algorithm='http://www.w3.org/2001/10/xml-exc-c14n#',
    )

    signed_root = signer.sign(
        root,
        key=private_key_pem,
        cert=cert_pem,
    )

    return etree.tostring(
        signed_root,
        pretty_print=True,
        xml_declaration=True,
        encoding='UTF-8',
    ).decode('utf-8')


def verify_signature(signed_xml_string, cert_pem):
    """
    Verify the XML signature of a signed document.

    Returns:
        bool: True if signature is valid
    """
    root = etree.fromstring(signed_xml_string.encode('utf-8'))
    verifier = XMLVerifier()

    try:
        verifier.verify(root, x509_cert=cert_pem)
        return True
    except Exception as e:
        logger.warning(f'Signature verification failed: {e}')
        return False
