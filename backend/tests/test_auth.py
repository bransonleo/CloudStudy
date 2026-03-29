"""Tests for auth_service: JWKS fetching and token verification."""
import json
import time
from unittest.mock import patch, MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app import create_app


# ── Fixtures ──────────────────────────────────────────────────────

def _generate_rsa_keypair():
    """Generate a test RSA key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key


def _build_jwks(public_key, kid="test-kid-1"):
    """Build a JWKS dict from a public key."""
    pub_numbers = public_key.public_numbers()
    import base64

    def _int_to_base64url(n, length=None):
        n_bytes = n.to_bytes((n.bit_length() + 7) // 8, byteorder="big")
        if length and len(n_bytes) < length:
            n_bytes = b"\x00" * (length - len(n_bytes)) + n_bytes
        return base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode("ascii")

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": _int_to_base64url(pub_numbers.n, 256),
                "e": _int_to_base64url(pub_numbers.e),
            }
        ]
    }


def _make_access_token(private_key, kid="test-kid-1", claims_override=None):
    """Create a signed JWT that mimics a Cognito access token."""
    now = int(time.time())
    claims = {
        "sub": "user-uuid-123",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool",
        "client_id": "test-client-id",
        "token_use": "access",
        "username": "testuser@example.com",
        "exp": now + 3600,
        "iat": now,
    }
    if claims_override:
        claims.update(claims_override)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


@pytest.fixture
def rsa_keys():
    return _generate_rsa_keypair()


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "COGNITO_USER_POOL_ID": "us-east-1_TestPool",
        "COGNITO_CLIENT_ID": "test-client-id",
        "COGNITO_REGION": "us-east-1",
        "COGNITO_JWKS_URL": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool/.well-known/jwks.json",
    })
    yield app


@pytest.fixture(autouse=True)
def clear_jwks_cache():
    """Clear the JWKS cache between tests."""
    from app.services import auth_service
    auth_service._jwks_cache.clear()
    yield
    auth_service._jwks_cache.clear()


# ── JWKS fetching ─────────────────────────────────────────────────

@patch("app.services.auth_service.requests.get")
def test_fetch_jwks_caches_keys(mock_get, rsa_keys, app):
    """First call fetches from network; second call uses cache."""
    _, pub = rsa_keys
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub)),
    )

    from app.services import auth_service
    with app.app_context():
        key1 = auth_service._get_public_key("test-kid-1")
        key2 = auth_service._get_public_key("test-kid-1")

    assert key1 is not None
    assert key1 is key2  # same object from cache
    mock_get.assert_called_once()  # only one HTTP call


@patch("app.services.auth_service.requests.get")
def test_fetch_jwks_refetches_on_unknown_kid(mock_get, rsa_keys, app):
    """Unknown kid triggers one re-fetch."""
    _, pub = rsa_keys
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub, kid="new-kid")),
    )

    from app.services import auth_service
    with app.app_context():
        key = auth_service._get_public_key("new-kid")

    assert key is not None


@patch("app.services.auth_service.requests.get")
def test_fetch_jwks_failure_raises(mock_get, app):
    """Network failure raises a clear error."""
    mock_get.side_effect = Exception("Connection refused")

    from app.services import auth_service
    with app.app_context():
        with pytest.raises(Exception, match="Failed to fetch JWKS"):
            auth_service._get_public_key("any-kid")


@patch("app.services.auth_service.requests.get")
def test_fetch_jwks_non_200_raises(mock_get, app):
    """Non-200 response raises a clear error."""
    mock_get.return_value = MagicMock(status_code=500)

    from app.services import auth_service
    with app.app_context():
        with pytest.raises(Exception, match="Failed to fetch JWKS"):
            auth_service._get_public_key("any-kid")


# ── Token verification ────────────────────────────────────────────

@patch("app.services.auth_service.requests.get")
def test_verify_valid_token(mock_get, rsa_keys, app):
    """Valid token returns decoded claims."""
    priv, pub = rsa_keys
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub)),
    )
    token = _make_access_token(priv)

    from app.services import auth_service
    with app.app_context():
        claims = auth_service.verify_token(token)

    assert claims["sub"] == "user-uuid-123"
    assert claims["username"] == "testuser@example.com"
    assert claims["token_use"] == "access"


@patch("app.services.auth_service.requests.get")
def test_verify_expired_token_raises(mock_get, rsa_keys, app):
    """Expired token raises InvalidTokenError."""
    priv, pub = rsa_keys
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub)),
    )
    token = _make_access_token(priv, claims_override={"exp": int(time.time()) - 100})

    from app.services import auth_service
    with app.app_context():
        with pytest.raises(auth_service.InvalidTokenError, match="expired"):
            auth_service.verify_token(token)


@patch("app.services.auth_service.requests.get")
def test_verify_wrong_issuer_raises(mock_get, rsa_keys, app):
    """Token with wrong issuer raises InvalidTokenError."""
    priv, pub = rsa_keys
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub)),
    )
    token = _make_access_token(priv, claims_override={
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_WRONG"
    })

    from app.services import auth_service
    with app.app_context():
        with pytest.raises(auth_service.InvalidTokenError):
            auth_service.verify_token(token)


@patch("app.services.auth_service.requests.get")
def test_verify_wrong_client_id_raises(mock_get, rsa_keys, app):
    """Token with wrong client_id raises InvalidTokenError."""
    priv, pub = rsa_keys
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub)),
    )
    token = _make_access_token(priv, claims_override={"client_id": "wrong-client"})

    from app.services import auth_service
    with app.app_context():
        with pytest.raises(auth_service.InvalidTokenError, match="client_id"):
            auth_service.verify_token(token)


@patch("app.services.auth_service.requests.get")
def test_verify_id_token_rejected(mock_get, rsa_keys, app):
    """Token with token_use='id' is rejected."""
    priv, pub = rsa_keys
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub)),
    )
    token = _make_access_token(priv, claims_override={"token_use": "id"})

    from app.services import auth_service
    with app.app_context():
        with pytest.raises(auth_service.InvalidTokenError, match="token_use"):
            auth_service.verify_token(token)


@patch("app.services.auth_service.requests.get")
def test_verify_invalid_signature_raises(mock_get, rsa_keys, app):
    """Token signed with wrong key is rejected."""
    _, pub = rsa_keys
    wrong_priv, _ = _generate_rsa_keypair()  # different key pair
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub)),
    )
    token = _make_access_token(wrong_priv)

    from app.services import auth_service
    with app.app_context():
        with pytest.raises(auth_service.InvalidTokenError):
            auth_service.verify_token(token)


@patch("app.services.auth_service.requests.get")
def test_verify_unknown_kid_after_refetch_raises(mock_get, rsa_keys, app):
    """Token with kid not in JWKS even after re-fetch raises error."""
    _, pub = rsa_keys
    priv2, _ = _generate_rsa_keypair()
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=_build_jwks(pub, kid="known-kid")),
    )
    # Token has kid="unknown-kid" which won't match even after re-fetch
    token = _make_access_token(priv2, kid="unknown-kid")

    from app.services import auth_service
    with app.app_context():
        with pytest.raises(auth_service.InvalidTokenError, match="kid"):
            auth_service.verify_token(token)


# ── Middleware: before_request hook ───────────────────────────────

class TestBeforeRequestHook:
    """Tests for the global before_request auth gate."""

    def test_health_endpoint_needs_no_token(self, app):
        """GET /api/health should work without any auth."""
        client = app.test_client()
        # Disable TESTING to exercise real before_request behavior
        app.config["TESTING"] = False
        response = client.get("/api/health")
        assert response.status_code == 200

    @patch("app.services.auth_service.verify_token")
    def test_protected_endpoint_without_token_returns_401(self, mock_verify, app):
        app.config["TESTING"] = False
        client = app.test_client()
        response = client.post("/api/upload")
        assert response.status_code == 401
        assert "Authorization" in response.get_json()["error"]

    @patch("app.services.auth_service.verify_token")
    def test_protected_endpoint_with_bad_scheme_returns_401(self, mock_verify, app):
        app.config["TESTING"] = False
        client = app.test_client()
        response = client.post(
            "/api/upload",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == 401

    @patch("app.services.auth_service.verify_token")
    def test_valid_token_sets_g_user_id(self, mock_verify, app):
        app.config["TESTING"] = False
        mock_verify.return_value = {
            "sub": "user-uuid-456",
            "username": "jane@example.com",
            "token_use": "access",
        }
        client = app.test_client()
        # Hit health to prime, then upload (which will fail on validation,
        # but auth should pass, giving us a 400 not a 401)
        response = client.post(
            "/api/upload",
            headers={"Authorization": "Bearer valid-test-token"},
        )
        # 400 = auth passed, route validation caught missing file
        assert response.status_code == 400
        mock_verify.assert_called_once_with("valid-test-token")

    @patch("app.services.auth_service.verify_token")
    def test_expired_token_returns_401(self, mock_verify, app):
        from app.services.auth_service import InvalidTokenError
        app.config["TESTING"] = False
        mock_verify.side_effect = InvalidTokenError("Token has expired")
        client = app.test_client()
        response = client.post(
            "/api/upload",
            headers={"Authorization": "Bearer expired-token"},
        )
        assert response.status_code == 401
        assert "expired" in response.get_json()["error"].lower()

    def test_testing_mode_sets_default_user(self, app):
        """In TESTING mode, before_request sets a default test user."""
        client = app.test_client()
        # TESTING is already True from the fixture
        # Upload will fail on validation but auth should be bypassed
        response = client.post("/api/upload")
        assert response.status_code == 400  # not 401


# ── Middleware: @require_auth decorator ───────────────────────────

class TestRequireAuthDecorator:
    """Tests for the @require_auth decorator."""

    @patch("app.services.auth_service.verify_token")
    def test_decorator_passes_when_g_user_id_set(self, mock_verify, app):
        """When before_request already set g.user_id, decorator passes through."""
        app.config["TESTING"] = False
        mock_verify.return_value = {
            "sub": "user-uuid-789",
            "username": "bob@example.com",
            "token_use": "access",
        }
        client = app.test_client()
        response = client.post(
            "/api/upload",
            headers={"Authorization": "Bearer test-token"},
        )
        # Auth passed (400 = file validation, not 401)
        assert response.status_code == 400
        # verify_token called once by before_request, not again by decorator
        mock_verify.assert_called_once()