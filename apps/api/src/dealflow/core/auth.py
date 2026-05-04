import time
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    aud: str | list[str]
    iss: str
    iat: int = 0
    exp: int = 0
    email: str | None = None
    name: str | None = None


class _JwksCache:
    """In-memory JWKS cache with TTL to avoid fetching on every request."""

    def __init__(self, ttl: int = 3600) -> None:
        self._data: dict[str, Any] = {}
        self._fetched_at: float = 0
        self._ttl = ttl

    def is_valid(self) -> bool:
        return bool(self._data) and (time.time() - self._fetched_at) < self._ttl

    def set(self, jwks: dict[str, Any]) -> None:
        self._data = jwks
        self._fetched_at = time.time()

    def get(self) -> dict[str, Any]:
        return self._data

    def invalidate(self) -> None:
        self._data = {}
        self._fetched_at = 0


_cache = _JwksCache()


async def fetch_jwks(domain: str, *, force: bool = False) -> dict[str, Any]:
    if not force and _cache.is_valid():
        return _cache.get()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"https://{domain}/.well-known/jwks.json")
        resp.raise_for_status()
    jwks = resp.json()
    _cache.set(jwks)
    return jwks


def _find_rsa_key(jwks: dict[str, Any], kid: str | None) -> dict[str, str] | None:
    for key in jwks.get("keys", []):
        if kid is None or key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key.get("kid", ""),
                "use": key.get("use", "sig"),
                "n": key["n"],
                "e": key["e"],
            }
    return None


_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "invalid_token", "message": "Could not validate credentials"},
    headers={"WWW-Authenticate": "Bearer"},
)


async def decode_jwt(token: str, domain: str, audience: str) -> TokenPayload:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise _CREDENTIALS_ERROR

    kid = header.get("kid")
    jwks = await fetch_jwks(domain)
    rsa_key = _find_rsa_key(jwks, kid)

    # Key not found — attempt one JWKS refresh to handle key rotation
    if rsa_key is None:
        jwks = await fetch_jwks(domain, force=True)
        rsa_key = _find_rsa_key(jwks, kid)

    if rsa_key is None:
        raise _CREDENTIALS_ERROR

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=f"https://{domain}/",
        )
    except JWTError:
        raise _CREDENTIALS_ERROR

    return TokenPayload(**payload)
