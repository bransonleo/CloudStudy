import uuid

from flask import Blueprint, current_app, jsonify, request

upload_bp = Blueprint("upload", __name__)


def _allowed_file(filename):
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", set())
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload. Validates file type and returns a stub response.

    S3 integration will replace the stub in a future task.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided", "status": 400}), 400

    file = request.files["file"]

    if file.filename == "" or file.filename is None:
        return jsonify({"error": "No file selected", "status": 400}), 400

    if not _allowed_file(file.filename):
        allowed = current_app.config.get("ALLOWED_EXTENSIONS", set())
        return (
            jsonify(
                {
                    "error": f"File type not allowed. Allowed: {', '.join(sorted(allowed))}",
                    "status": 400,
                }
            ),
            400,
        )

    material_id = str(uuid.uuid4())

    # TODO: Replace with S3 upload (s3_service.upload_file)
    # For now, just read the file to confirm it's valid
    file.read()

    return jsonify(
        {
            "material_id": material_id,
            "filename": file.filename,
            "message": "File uploaded successfully",
        }
    )
