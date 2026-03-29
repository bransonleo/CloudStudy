from unittest.mock import patch


@patch("app.routes.results.db_service.get_material_with_results")
def test_results_returns_200_with_all_keys(mock_get, client):
    mock_get.return_value = {
        "material_id": "mat-1",
        "filename": "notes.txt",
        "status": "ready",
        "error_message": None,
        "results": {
            "summary": {"status": "done", "content": {"title": "T"}},
            "quiz": {"status": "done", "content": {"questions": []}},
            "flashcards": {"status": "not_requested"},
        },
    }
    response = client.get("/api/results/mat-1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["material_id"] == "mat-1"
    assert "summary" in data["results"]
    assert "quiz" in data["results"]
    assert "flashcards" in data["results"]


@patch("app.routes.results.db_service.get_material_with_results")
def test_results_absent_types_show_not_requested(mock_get, client):
    mock_get.return_value = {
        "material_id": "mat-1",
        "filename": "notes.txt",
        "status": "extracting",
        "error_message": None,
        "results": {
            "summary": {"status": "not_requested"},
            "quiz": {"status": "not_requested"},
            "flashcards": {"status": "not_requested"},
        },
    }
    response = client.get("/api/results/mat-1")
    data = response.get_json()
    assert data["results"]["summary"]["status"] == "not_requested"


@patch("app.routes.results.db_service.get_material_with_results")
def test_results_not_found_returns_404(mock_get, client):
    mock_get.return_value = None
    response = client.get("/api/results/nonexistent")
    assert response.status_code == 404
