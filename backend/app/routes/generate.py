from flask import Blueprint, g, jsonify, request

from app import pipeline
from app.middleware.auth import require_auth

generate_bp = Blueprint("generate", __name__)

VALID_TYPES = {"summary", "quiz", "flashcards"}


@generate_bp.route("/generate/<material_id>", methods=["POST"])
@require_auth
def generate(material_id):
    """Generate AI content (summary, quiz, or flashcards) for an uploaded material."""
    body = request.get_json(silent=True) or {}
    result_type = body.get("type")

    if not result_type or result_type not in VALID_TYPES:
        return (
            jsonify({"error": "type must be one of: summary, quiz, flashcards", "status": 400}),
            400,
        )

    format_hint = body.get("format_hint")

    try:
        result = pipeline.run_generation(
            material_id, result_type, format_hint, user_id=g.user_id
        )
        return jsonify(result), 200
    except pipeline.MaterialNotFound:
        return jsonify({"error": "Material not found", "status": 404}), 404
    except pipeline.MaterialNotReady:
        return jsonify({"error": "Material still processing", "status": 409}), 409
    except pipeline.MaterialFailed as e:
        return jsonify({"error": f"Text extraction failed: {e}", "status": 422}), 422
    except Exception as e:
        return jsonify({"error": str(e), "status": 500}), 500
