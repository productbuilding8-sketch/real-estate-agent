"""DAI-010: Auth0 JWT validation tests.

All tests mock the JWKS endpoint — no real Auth0 tenant needed.
The JWT is signed with a locally generated RSA key pair and verified
end-to-end through the same decode_jwt() path used in production.
"""

from unittest.mock import AsyncMock, patch

import pytest

# ── shared key pair for the test session ──────────────────────────────────────
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient

from dealflow.config import Settings
from dealflow.core.auth import TokenPayload, decode_jwt
from tests.helpers.jwt_factory import (
    TEST_AUDIENCE,
    TEST_DOMAIN,
    build_jwks,
    generate_rsa_keypair,
    make_token,
)


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return generate_rsa_keypair()


@pytest.fixture(scope="module")
def jwks(rsa_key: rsa.RSAPrivateKey) -> dict:
    return build_jwks(rsa_key)


@pytest.fixture
def valid_token(rsa_key: rsa.RSAPrivateKey) -> str:
    return make_token(rsa_key)


# ── unit tests: decode_jwt() ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_token_decodes(valid_token: str, jwks: dict) -> None:
    with patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=jwks)):
        payload = await decode_jwt(valid_token, TEST_DOMAIN, TEST_AUDIENCE)

    assert isinstance(payload, TokenPayload)
    assert payload.sub == "auth0|test_user_123"
    assert payload.email == "test@example.com"
    assert payload.name == "Test User"


@pytest.mark.asyncio
async def test_expired_token_raises_401(rsa_key: rsa.RSAPrivateKey, jwks: dict) -> None:
    expired = make_token(rsa_key, exp_offset=-60)
    with patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=jwks)):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await decode_jwt(expired, TEST_DOMAIN, TEST_AUDIENCE)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_wrong_audience_raises_401(rsa_key: rsa.RSAPrivateKey, jwks: dict) -> None:
    wrong_aud = make_token(rsa_key, audience="https://wrong.audience.com")
    with patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=jwks)):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await decode_jwt(wrong_aud, TEST_DOMAIN, TEST_AUDIENCE)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_wrong_signature_raises_401(jwks: dict) -> None:
    other_key = generate_rsa_keypair()
    forged = make_token(other_key)
    with patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=jwks)):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await decode_jwt(forged, TEST_DOMAIN, TEST_AUDIENCE)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_garbage_token_raises_401(jwks: dict) -> None:
    from fastapi import HTTPException

    with (
        patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=jwks)),
        pytest.raises(HTTPException) as exc,
    ):
        await decode_jwt("not.a.jwt", TEST_DOMAIN, TEST_AUDIENCE)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_unknown_kid_refreshes_cache_then_fails(
    rsa_key: rsa.RSAPrivateKey,
) -> None:
    token = make_token(rsa_key, kid="unknown-kid")
    empty_jwks: dict = {"keys": []}
    with patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=empty_jwks)):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await decode_jwt(token, TEST_DOMAIN, TEST_AUDIENCE)
    assert exc.value.status_code == 401


# ── route tests: GET /api/v1/auth/me ─────────────────────────────────────────


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        auth0_domain=TEST_DOMAIN,
        auth0_audience=TEST_AUDIENCE,
        secret_key="test-secret",
        environment="test",
    )


@pytest.fixture
async def auth_client(auth_settings: Settings) -> AsyncClient:
    from httpx import ASGITransport, AsyncClient

    from dealflow.main import create_app

    app = create_app(auth_settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_me_returns_user_info(
    auth_client: AsyncClient,
    valid_token: str,
    jwks: dict,
) -> None:
    with patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=jwks)):
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["sub"] == "auth0|test_user_123"
    assert body["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "missing_token"


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(auth_client: AsyncClient, jwks: dict) -> None:
    with patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=jwks)):
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
