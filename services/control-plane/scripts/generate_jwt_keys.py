import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_jwt_keys(
    private_key_path: Path = Path("keys/private.pem"),
    public_key_path: Path = Path("keys/public.pem"),
) -> None:
    if private_key_path.exists():
        print(
            f"Error: Private key already exists at {private_key_path}. Refusing to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    if public_key_path.exists():
        print(
            f"Error: Public key already exists at {public_key_path}. Refusing to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path.parent.mkdir(parents=True, exist_ok=True)

    private_key_path.write_bytes(private_pem)
    public_key_path.write_bytes(public_pem)

    print(f"Generated RSA 2048 keys:\n  Private: {private_key_path}\n  Public:  {public_key_path}")


if __name__ == "__main__":
    generate_jwt_keys()

