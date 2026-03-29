import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.services import db_service


@pytest.fixture
def app():
    app = create_app({"TESTING": True})
    return app


@patch("app.services.db_service._get_connection")
def test_create_tables_executes_two_creates(mock_get_conn, app):
    """create_tables should issue CREATE TABLE IF NOT EXISTS for both tables."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with app.app_context():
        db_service.create_tables()

    assert mock_cursor.execute.call_count == 2
    calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
    assert any("materials" in sql for sql in calls)
    assert any("results" in sql for sql in calls)
    mock_conn.close.assert_called_once()


@patch("app.services.db_service._get_connection")
def test_create_material_inserts_row(mock_get_conn, app):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with app.app_context():
        db_service.create_material("mat-1", "notes.txt", "uploads/mat-1/notes.txt", "txt")

    sql, params = mock_cursor.execute.call_args[0]
    assert "INSERT INTO materials" in sql
    assert params[0] == "mat-1"
    assert params[1] == "notes.txt"
    assert params[2] == "uploads/mat-1/notes.txt"
    assert params[3] == "txt"


@patch("app.services.db_service._get_connection")
def test_update_material_updates_status(mock_get_conn, app):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with app.app_context():
        db_service.update_material("mat-1", status="ready", extracted_text="some text")

    sql, params = mock_cursor.execute.call_args[0]
    assert "UPDATE materials" in sql
    assert "ready" in params
    assert "some text" in params
    assert "mat-1" in params
