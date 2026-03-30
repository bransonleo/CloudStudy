"""Auth middleware: before_request hook and @require_auth decorator."""
from functools import wraps

from flask import g, jsonify, request

from app.services import auth_service as _auth_service
from app.services.auth_service import InvalidTokenError


# Endpoints that do not require authentication
PUBLIC_PATHS = {"/api/health"}


def register_auth_middleware(app):
    """Register the before_request hook that enforces auth on all
    non-public endpoints. Call this in the app factory."""

    @app.before_request
    def _verify_auth():
        # Skip CORS preflight
        if request.method == "OPTIONS":
            return None

        # Skip public endpoints
        if request.path in PUBLIC_PATHS:
            return None

        # In test mode: set default test user, skip verification
        if app.config.get("TESTING"):
            g.user_id = "test-user"
            g.user_email = "test@example.com"
            return None

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return (
                jsonify({
                    "error": "Missing or invalid Authorization header",
                    "status": 401,
                }),
                401,
            )

        token = auth_header.split(" ", 1)[1]

        try:
            claims = _auth_service.verify_token(token)
        except InvalidTokenError as e:
            return (
                jsonify({"error": str(e), "status": 401}),
                401,
            )

        # Set user identity on Flask g
        g.user_id = claims["sub"]
        g.user_email = claims.get("username", "")

        return None


def require_auth(f):
    """Per-route decorator: second auth layer (defense-in-depth).

    If before_request already verified the token, this passes through.
    If not (e.g., before_request was bypassed), performs verification itself.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip CORS preflight
        if request.method == "OPTIONS":
            return f(*args, **kwargs)

        # If before_request already set user identity, pass through
        if getattr(g, "user_id", None):
            return f(*args, **kwargs)

        # Self-sufficient fallback: verify token ourselves
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return (
                jsonify({
                    "error": "Missing or invalid Authorization header",
                    "status": 401,
                }),
                401,
            )

        token = auth_header.split(" ", 1)[1]

        try:
            claims = _auth_service.verify_token(token)
        except InvalidTokenError as e:
            return jsonify({"error": str(e), "status": 401}), 401

        g.user_id = claims["sub"]
        g.user_email = claims.get("username", "")

        return f(*args, **kwargs)

    return decorated