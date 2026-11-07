"""Generate weak + normal EC test certificates for offline engine tests.

Writes (into /engines/tests/fixtures):
  - weak_self_signed.pem: self-signed cert whose EC private key is tiny (k = 4)
  - normal_self_signed.pem: self-signed cert with a normal EC private key

Test fixtures only - not used by the engine at runtime.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
WEAK_CERT_NAME = "weak_self_signed.pem"
NORMAL_CERT_NAME = "normal_self_signed.pem"


def _build(subject_cn: str, san_dns: str, private_key) -> x509.Certificate:
    now = datetime.now(timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_cn)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_cn)]))
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(san_dns)]), critical=False)
        .sign(private_key, hashes.SHA256())
    )


def generate() -> None:
    # Weak: EC private scalar k = 4 -> public key = 4 * G (trivially guessable).
    weak_private_key = ec.derive_private_key(4, ec.SECP256R1())
    weak_cert = _build("weak-test.example.com", "weak-test.example.com", weak_private_key)
    (FIXTURE_DIR / WEAK_CERT_NAME).write_bytes(
        weak_cert.public_bytes(serialization.Encoding.PEM)
    )

    # Normal: random EC private key (public key = private * G, private is large).
    normal_private_key = ec.generate_private_key(ec.SECP256R1())
    normal_cert = _build("normal-test.example.com", "normal-test.example.com", normal_private_key)
    (FIXTURE_DIR / NORMAL_CERT_NAME).write_bytes(
        normal_cert.public_bytes(serialization.Encoding.PEM)
    )

    print(f"wrote {FIXTURE_DIR / WEAK_CERT_NAME}")
    print(f"wrote {FIXTURE_DIR / NORMAL_CERT_NAME}")


if __name__ == "__main__":
    generate()
