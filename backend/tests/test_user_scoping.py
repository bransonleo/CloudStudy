"""Tests that verify user data isolation across endpoints."""
import io
from unittest.mock import patch, MagicMock

import pytest
from flask import g

from app import create_app


@pytest.fixture
def app():
    app = create_app({"TESTING": True})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


# ── Upload scoping ────────────────────────────────────────────────

@patch("app.routes.upload.pipeline.start_upload_job")
def test_upload_passes_test_user_id(mock_start, client):
    """In test mode, upload passes the default test user_id to pipeline."""
    mock_start.return_value = "mat-1"
    data = {"file": (io.BytesIO(b"notes"), "notes.txt")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 202
    # Verify user_id was passed as the third argument
    call_args = mock_start.call_args[0]
    assert call_args[2] == "test-user"


# ── Results scoping ──────────────────────────────────────────────

@patch("app.routes.results.db_service.get_material_with_results")
def test_results_passes_user_id_to_db(mock_get, client):
    """Results endpoint passes user_id for ownership filtering."""
    mock_get.return_value = {
        "material_id": "mat-1",
        "filename": "notes.txt",
        "status": "ready",
        "error_message": None,
        "results": {
            "summary": {"status": "not_requested"},
            "quiz": {"status": "not_requested"},
            "flashcards": {"status": "not_requested"},
        },
    }
    response = client.get("/api/results/mat-1")
    assert response.status_code == 200
    mock_get.assert_called_once_with("mat-1", "test-user")


@patch("app.routes.results.db_service.get_material_with_results")
def test_results_returns_404_for_other_users_material(mock_get, client):
    """When db returns None (user_id mismatch), route returns 404."""
    mock_get.return_value = None
    response = client.get("/api/results/other-users-mat")
    assert response.status_code == 404


# ── Generate scoping ─────────────────────────────────────────────

@patch("app.routes.generate.pipeline.run_generation")
def test_generate_passes_user_id(mock_run, client):
    """Generate endpoint passes user_id to pipeline."""
    mock_run.return_value = {
        "result_id": "res-1",
        "material_id": "mat-1",
        "type": "summary",
        "content": {"title": "T", "key_points": [], "summary": "S"},
        "format_hint": None,
    }
    response = client.post(
        "/api/generate/mat-1",
        json={"type": "summary"},
        content_type="application/json",
    )
    assert response.status_code == 200
    mock_run.assert_called_once_with("mat-1", "summary", None, user_id="test-user")


@patch("app.routes.generate.pipeline.run_generation")
def test_generate_returns_404_for_other_users_material(mock_run, client):
    """When pipeline raises MaterialNotFound (user_id mismatch), route returns 404."""
    from app.pipeline import MaterialNotFound
    mock_run.side_effect = MaterialNotFound("mat-1")
    response = client.post(
        "/api/generate/mat-1",
        json={"type": "summary"},
        content_type="application/json",
    )
    assert response.status_code == 404
