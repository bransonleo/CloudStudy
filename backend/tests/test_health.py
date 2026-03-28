def test_health_returns_ok(client):
    """GET /api/health should return 200 with status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_health_returns_json_content_type(client):
    """Health endpoint should return application/json."""
    response = client.get("/api/health")
    assert "application/json" in response.content_type


def test_not_found_returns_json(client):
    """Unknown routes should return structured JSON 404."""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "Not found"
    assert data["status"] == 404
