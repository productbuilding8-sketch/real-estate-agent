"""Test helpers for generating signed JWTs and matching JWKS fixtures."""

import base64
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

TEST_DOMAIN = "test.auth0.com"
TEST_AUDIENCE = "https://api.dealflow.test"
TEST_KID = "test-key-001"


def _int_to_base64url(n: int) -> str:
    byte_len = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(byte_len, "big")).rstrip(b"=").decode()


def generate_rsa_keypair() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def private_key_to_pem(private_key: rsa.RSAPrivateKey) -> bytes:
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def build_jwks(private_key: rsa.RSAPrivateKey, kid: str = TEST_KID) -> dict:
    pub_numbers = private_key.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": _int_to_base64url(pub_numbers.n),
                "e": _int_to_base64url(pub_numbers.e),
            }
        ]
    }


def make_token(
    private_key: rsa.RSAPrivateKey,
    *,
    sub: str = "auth0|test_user_123",
    audience: str = TEST_AUDIENCE,
    domain: str = TEST_DOMAIN,
    kid: str = TEST_KID,
    exp_offset: int = 3600,
    email: str = "test@example.com",
    name: str = "Test User",
) -> str:
    payload = {
        "sub": sub,
        "aud": audience,
        "iss": f"https://{domain}/",
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
        "email": email,
        "name": name,
    }
    return jwt.encode(
        payload,
        private_key_to_pem(private_key),
        algorithm="RS256",
        headers={"kid": kid},
    )
