# backend/tests/test_pipeline.py
import io
from unittest.mock import patch, MagicMock
import pytest
from app import pipeline


@patch("app.pipeline.db_service.create_material")
@patch("app.pipeline.s3_service.upload_file")
def test_start_upload_job_returns_material_id(mock_upload, mock_create, app):
    mock_file = MagicMock()
    mock_file.filename = "notes.txt"
    mock_file.content_type = "text/plain"

    with app.app_context():
        material_id = pipeline.start_upload_job(mock_file, app)

    assert len(material_id) == 36  # UUID format
    mock_upload.assert_called_once()
    upload_args = mock_upload.call_args[0]
    assert upload_args[1] == f"uploads/{material_id}/notes.txt"
    mock_create.assert_called_once()


@patch("app.pipeline.db_service.create_material")
@patch("app.pipeline.s3_service.upload_file")
def test_start_upload_job_starts_daemon_thread(mock_upload, mock_create, app):
    mock_file = MagicMock()
    mock_file.filename = "notes.txt"
    mock_file.content_type = "text/plain"

    with patch("app.pipeline.threading.Thread") as mock_thread_cls:
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread
        with app.app_context():
            pipeline.start_upload_job(mock_file, app)

    mock_thread_cls.assert_called_once()
    assert mock_thread_cls.call_args[1]["daemon"] is True
    mock_thread.start.assert_called_once()


@patch("app.pipeline.db_service.update_material")
@patch("app.pipeline.ocr_service.extract_text")
@patch("app.pipeline.s3_service.get_file_bytes")
def test_run_ocr_success_sets_ready(mock_bytes, mock_ocr, mock_update, app):
    mock_bytes.return_value = io.BytesIO(b"content")
    mock_ocr.return_value = "extracted text"

    pipeline._run_ocr(app, "mat-1", "uploads/mat-1/notes.txt", "text/plain")

    mock_update.assert_called_once_with(
        "mat-1", status="ready", extracted_text="extracted text"
    )


@patch("app.pipeline.db_service.update_material")
@patch("app.pipeline.s3_service.get_file_bytes")
def test_run_ocr_failure_sets_error(mock_bytes, mock_update, app):
    mock_bytes.side_effect = Exception("S3 connection failed")

    pipeline._run_ocr(app, "mat-1", "uploads/mat-1/notes.txt", "text/plain")

    mock_update.assert_called_once_with(
        "mat-1", status="error", error_message="S3 connection failed"
    )


@patch("app.pipeline.db_service.save_result")
@patch("app.pipeline.ai_service.generate")
@patch("app.pipeline.db_service.get_material")
def test_run_generation_success(mock_get, mock_ai, mock_save, app):
    mock_get.return_value = {"id": "mat-1", "status": "ready", "extracted_text": "text"}
    mock_ai.return_value = {"title": "Notes", "key_points": [], "summary": "S"}
    mock_save.return_value = "result-uuid"

    with app.app_context():
        result = pipeline.run_generation("mat-1", "summary")

    assert result["material_id"] == "mat-1"
    assert result["content"]["title"] == "Notes"


@patch("app.pipeline.db_service.get_material")
def test_run_generation_raises_not_found(mock_get, app):
    mock_get.return_value = None
    with app.app_context():
        with pytest.raises(pipeline.MaterialNotFound):
            pipeline.run_generation("nonexistent", "summary")


@patch("app.pipeline.db_service.get_material")
def test_run_generation_raises_not_ready(mock_get, app):
    mock_get.return_value = {"id": "mat-1", "status": "extracting"}
    with app.app_context():
        with pytest.raises(pipeline.MaterialNotReady):
            pipeline.run_generation("mat-1", "summary")


@patch("app.pipeline.db_service.get_material")
def test_run_generation_raises_material_failed(mock_get, app):
    mock_get.return_value = {"id": "mat-1", "status": "error", "error_message": "Textract timeout"}
    with app.app_context():
        with pytest.raises(pipeline.MaterialFailed):
            pipeline.run_generation("mat-1", "summary")


@patch("app.pipeline.db_service.save_result")
@patch("app.pipeline.ai_service.generate")
@patch("app.pipeline.db_service.get_material")
def test_run_generation_saves_error_on_ai_failure(mock_get, mock_ai, mock_save, app):
    mock_get.return_value = {"id": "mat-1", "status": "ready", "extracted_text": "text"}
    mock_ai.side_effect = ValueError("AI response could not be parsed")

    with app.app_context():
        with pytest.raises(ValueError):
            pipeline.run_generation("mat-1", "summary")

    mock_save.assert_called_once_with(
        "mat-1", "summary", status="error",
        error_message="AI response could not be parsed"
    )
