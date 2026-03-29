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
