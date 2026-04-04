# backend/app/pipeline.py
import threading
import uuid

from app.services import db_service, s3_service, ocr_service, ai_service


class MaterialNotFound(Exception):
    pass


class MaterialNotReady(Exception):
    pass


class MaterialFailed(Exception):
    pass


def start_upload_job(file, app, user_id):
    """Upload file to S3, create DB record, start background OCR thread.
    Returns material_id immediately."""
    material_id = str(uuid.uuid4())
    filename = file.filename
    file_type = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    s3_key = f"uploads/{material_id}/{filename}"

    s3_service.upload_file(file, s3_key)
    db_service.create_material(material_id, filename, s3_key, file_type, user_id)

    thread = threading.Thread(
        target=_run_ocr,
        args=(app, material_id, s3_key, file.content_type),
        daemon=True,
    )
    thread.start()
    return material_id


def _run_ocr(app, material_id, s3_key, content_type):
    """Background thread: extract text from S3 file and update DB status."""
    with app.app_context():
        try:
            file_bytes = s3_service.get_file_bytes(s3_key)
            text = ocr_service.extract_text(file_bytes, content_type)
            db_service.update_material(material_id, status="ready", extracted_text=text)
        except Exception as e:
            db_service.update_material(
                material_id, status="error", error_message=str(e)
            )


def run_generation(material_id, result_type, format_hint=None, user_id=None, api_key=None):
    """Run Gemini generation synchronously. Returns result dict.
    Raises MaterialNotFound, MaterialNotReady, or MaterialFailed on pipeline errors."""
    material = db_service.get_material(material_id, user_id)
    if not material:
        raise MaterialNotFound(material_id)
    if material["status"] == "extracting":
        raise MaterialNotReady()
    if material["status"] == "error":
        raise MaterialFailed(material.get("error_message", "OCR failed"))

    try:
        content = ai_service.generate(
            material["extracted_text"], result_type, format_hint, api_key=api_key
        )
    except Exception as e:
        db_service.save_result(
            material_id, result_type, status="error", error_message=str(e)
        )
        raise

    result_id = db_service.save_result(
        material_id, result_type, status="done",
        content=content, format_hint=format_hint,
    )
    return {
        "result_id": result_id,
        "material_id": material_id,
        "type": result_type,
        "content": content,
        "format_hint": format_hint,
    }
