import io
from unittest.mock import patch


def test_upload_no_file_returns_400(client):
    response = client.post("/api/upload")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_upload_empty_filename_returns_400(client):
    data = {"file": (io.BytesIO(b""), "")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 400


def test_upload_invalid_extension_returns_400(client):
    data = {"file": (io.BytesIO(b"malicious"), "virus.exe")}
    response = client.post(
        "/api/upload", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert "not allowed" in response.get_json()["error"].lower()


@patch("app.routes.upload.pipeline.start_upload_job")
def test_upload_valid_txt_returns_202(mock_start, client):
    mock_start.return_value = "test-material-id"
    data = {"file": (io.BytesIO(b"Hello, study notes!"), "notes.txt")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 202
    result = response.get_json()
    assert result["material_id"] == "test-material-id"
    assert result["status"] == "extracting"


@patch("app.routes.upload.pipeline.start_upload_job")
def test_upload_valid_pdf_returns_202(mock_start, client):
    mock_start.return_value = "test-material-id"
    data = {"file": (io.BytesIO(b"%PDF-fake"), "lecture.pdf")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 202
    result = response.get_json()
    assert result["material_id"] == "test-material-id"
