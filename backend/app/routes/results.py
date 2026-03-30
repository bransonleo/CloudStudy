from flask import Blueprint, g, jsonify

from app.middleware.auth import require_auth
from app.services import db_service

results_bp = Blueprint("results", __name__)


@results_bp.route("/results/<material_id>", methods=["GET"])
@require_auth
def get_results(material_id):
    """Return material status and all generated content."""
    data = db_service.get_material_with_results(material_id, g.user_id)
    if not data:
        return jsonify({"error": "Material not found", "status": 404}), 404
    return jsonify(data), 200
