"""Cognito JWT verification via JWKS public keys."""
import threading

import jwt
import requests
from flask import current_app


class InvalidTokenError(Exception):
    """Raised when a JWT fails verification."""
    pass


# Module-level cache: {kid: RSA public key object}
_jwks_cache = {}
_jwks_lock = threading.Lock()


def _fetch_jwks():
    """Fetch JWKS from Cognito and update the cache."""
    url = current_app.config["COGNITO_JWKS_URL"]
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            raise Exception(f"Failed to fetch JWKS: HTTP {resp.status_code}")
        jwks = resp.json()
    except Exception as e:
        if "Failed to fetch JWKS" in str(e):
            raise
        raise Exception(f"Failed to fetch JWKS: {e}") from e

    with _jwks_lock:
        for key_data in jwks.get("keys", []):
            kid = key_data["kid"]
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            _jwks_cache[kid] = public_key


def _get_public_key(kid):
    """Get the RSA public key for a given kid, fetching JWKS if needed."""
    # Try cache first
    with _jwks_lock:
        if kid in _jwks_cache:
            return _jwks_cache[kid]

    # Cache miss: fetch JWKS
    _fetch_jwks()

    with _jwks_lock:
        if kid in _jwks_cache:
            return _jwks_cache[kid]

    # Still not found after re-fetch: try one more time (key rotation)
    _fetch_jwks()

    with _jwks_lock:
        if kid in _jwks_cache:
            return _jwks_cache[kid]

    raise InvalidTokenError(f"Unknown kid: {kid}")


def verify_token(token):
    """Verify a Cognito access token and return its claims.

    Validates: signature (RS256), expiration, issuer, client_id, token_use.
    Raises InvalidTokenError on any failure.
    """
    config = current_app.config
    region = config.get("COGNITO_REGION", "us-east-1")
    pool_id = config.get("COGNITO_USER_POOL_ID", "")
    client_id = config.get("COGNITO_CLIENT_ID", "")
    expected_issuer = (
        f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
    )

    try:
        # Read header without verification to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise InvalidTokenError("Token header missing kid")

        public_key = _get_public_key(kid)

        # Decode and verify signature, expiration, issuer
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=expected_issuer,
            options={"verify_aud": False},
        )

        # Validate client_id (Cognito access tokens use this instead of aud)
        if claims.get("client_id") != client_id:
            raise InvalidTokenError(
                f"Invalid client_id: expected {client_id}, "
                f"got {claims.get('client_id')}"
            )

        # Validate token_use
        if claims.get("token_use") != "access":
            raise InvalidTokenError(
                f"Invalid token_use: expected 'access', "
                f"got '{claims.get('token_use')}'"
            )

        return claims

    except InvalidTokenError:
        raise
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token has expired")
    except jwt.InvalidIssuerError:
        raise InvalidTokenError("Invalid issuer")
    except jwt.InvalidSignatureError:
        raise InvalidTokenError("Invalid signature")
    except jwt.DecodeError as e:
        raise InvalidTokenError(f"Token decode failed: {e}")
    except Exception as e:
        raise InvalidTokenError(f"Token verification failed: {e}")