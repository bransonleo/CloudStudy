from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health_check():
    """Basic health check for ALB and monitoring."""
    return jsonify({"status": "ok"})
