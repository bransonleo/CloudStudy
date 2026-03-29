from unittest.mock import patch
from app import pipeline


def test_generate_missing_type_returns_400(client):
    response = client.post("/api/generate/mat-1", json={}, content_type="application/json")
    assert response.status_code == 400
    assert "type" in response.get_json()["error"].lower()


def test_generate_invalid_type_returns_400(client):
    response = client.post(
        "/api/generate/mat-1", json={"type": "essay"}, content_type="application/json"
    )
    assert response.status_code == 400


@patch("app.routes.generate.pipeline.run_generation")
def test_generate_success_returns_200(mock_run, client):
    mock_run.return_value = {
        "result_id": "res-1", "material_id": "mat-1", "type": "summary",
        "content": {"title": "Notes", "key_points": [], "summary": "S"},
        "format_hint": None,
    }
    response = client.post(
        "/api/generate/mat-1", json={"type": "summary"}, content_type="application/json"
    )
    assert response.status_code == 200
    assert response.get_json()["content"]["title"] == "Notes"


@patch("app.routes.generate.pipeline.run_generation")
def test_generate_not_found_returns_404(mock_run, client):
    mock_run.side_effect = pipeline.MaterialNotFound("mat-1")
    response = client.post(
        "/api/generate/mat-1", json={"type": "summary"}, content_type="application/json"
    )
    assert response.status_code == 404


@patch("app.routes.generate.pipeline.run_generation")
def test_generate_extracting_returns_409(mock_run, client):
    mock_run.side_effect = pipeline.MaterialNotReady()
    response = client.post(
        "/api/generate/mat-1", json={"type": "summary"}, content_type="application/json"
    )
    assert response.status_code == 409


@patch("app.routes.generate.pipeline.run_generation")
def test_generate_ocr_error_returns_422(mock_run, client):
    mock_run.side_effect = pipeline.MaterialFailed("Textract error")
    response = client.post(
        "/api/generate/mat-1", json={"type": "summary"}, content_type="application/json"
    )
    assert response.status_code == 422
    assert "Textract error" in response.get_json()["error"]


@patch("app.routes.generate.pipeline.run_generation")
def test_generate_ai_failure_returns_500(mock_run, client):
    mock_run.side_effect = ValueError("AI response could not be parsed")
    response = client.post(
        "/api/generate/mat-1", json={"type": "quiz"}, content_type="application/json"
    )
    assert response.status_code == 500
    assert "AI response could not be parsed" in response.get_json()["error"]
