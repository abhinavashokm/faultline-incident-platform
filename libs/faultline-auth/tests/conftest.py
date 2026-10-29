import json
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm


@pytest.fixture(scope="session")
def rsa_keypair():
    """Generate an RSA 2048 keypair with kid, PEMs, and JWKS dict."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    kid = "test-key-1"
    jwk_dict = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk_dict["kid"] = kid
    jwk_dict["use"] = "sig"
    jwk_dict["alg"] = "RS256"

    jwks_dict = {"keys": [jwk_dict]}

    return {
        "private_key": private_key,
        "public_key": public_key,
        "private_pem": priv_pem,
        "public_pem": pub_pem,
        "kid": kid,
        "jwk": jwk_dict,
        "jwks": jwks_dict,
    }

