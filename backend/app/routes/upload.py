from flask import Blueprint, current_app, g, jsonify, request

from app import pipeline
from app.middleware.auth import require_auth

upload_bp = Blueprint("upload", __name__)


def _allowed_file(filename):
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", set())
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@upload_bp.route("/upload", methods=["POST"])
@require_auth
def upload_file():
    """Upload a file to S3 and start background OCR."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided", "status": 400}), 400

    file = request.files["file"]

    if file.filename == "" or file.filename is None:
        return jsonify({"error": "No file selected", "status": 400}), 400

    if not _allowed_file(file.filename):
        allowed = current_app.config.get("ALLOWED_EXTENSIONS", set())
        return (
            jsonify({
                "error": f"File type not allowed. Allowed: {', '.join(sorted(allowed))}",
                "status": 400,
            }),
            400,
        )

    try:
        material_id = pipeline.start_upload_job(
            file, current_app._get_current_object(), g.user_id
        )
    except Exception:
        return jsonify({"error": "Upload failed", "status": 500}), 500

    return jsonify({"material_id": material_id, "status": "extracting"}), 202
