import io


def test_upload_no_file_returns_400(client):
    """POST /api/upload with no file should return 400."""
    response = client.post("/api/upload")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_upload_empty_filename_returns_400(client):
    """POST /api/upload with empty filename should return 400."""
    data = {"file": (io.BytesIO(b""), "")}
    response = client.post(
        "/api/upload", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 400


def test_upload_invalid_extension_returns_400(client):
    """POST /api/upload with .exe file should return 400."""
    data = {"file": (io.BytesIO(b"malicious"), "virus.exe")}
    response = client.post(
        "/api/upload", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert "not allowed" in response.get_json()["error"].lower()


def test_upload_valid_txt_returns_200(client):
    """POST /api/upload with a .txt file should return 200."""
    data = {"file": (io.BytesIO(b"Hello, study notes!"), "notes.txt")}
    response = client.post(
        "/api/upload", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 200
    result = response.get_json()
    assert result["filename"] == "notes.txt"
    assert "material_id" in result


def test_upload_valid_pdf_returns_200(client):
    """POST /api/upload with a .pdf file should return 200."""
    data = {"file": (io.BytesIO(b"%PDF-fake"), "lecture.pdf")}
    response = client.post(
        "/api/upload", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 200
    result = response.get_json()
    assert result["filename"] == "lecture.pdf"
