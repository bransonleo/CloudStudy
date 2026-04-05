import io
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.services import db_service, s3_service, ocr_service, ai_service


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
        db_service.create_material("mat-1", "notes.txt", "uploads/mat-1/notes.txt", "txt", "user-123")

    sql, params = mock_cursor.execute.call_args[0]
    assert "INSERT INTO materials" in sql
    assert "user_id" in sql
    assert params[0] == "mat-1"
    assert params[1] == "notes.txt"
    assert params[2] == "uploads/mat-1/notes.txt"
    assert params[3] == "txt"
    assert params[4] == "user-123"


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


@patch("app.services.db_service._get_connection")
def test_get_material_returns_row(mock_get_conn, app):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"id": "mat-1", "filename": "notes.txt", "status": "ready"}
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with app.app_context():
        row = db_service.get_material("mat-1", "user-123")

    assert row["id"] == "mat-1"
    assert row["status"] == "ready"
    sql, params = mock_cursor.execute.call_args[0]
    assert "user_id" in sql
    assert "user-123" in params


@patch("app.services.db_service._get_connection")
def test_get_material_returns_none_when_missing(mock_get_conn, app):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with app.app_context():
        row = db_service.get_material("nonexistent", "user-123")

    assert row is None


@patch("app.services.db_service._get_connection")
def test_save_result_inserts_new_row(mock_get_conn, app):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # SELECT returns None — no existing row
    mock_cursor.fetchone.return_value = None
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with app.app_context():
        result_id = db_service.save_result("mat-1", "summary", "done", content={"title": "Notes"})

    assert result_id is not None
    assert len(result_id) == 36  # UUID format
    calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
    assert any("INSERT INTO results" in sql for sql in calls)


@patch("app.services.db_service._get_connection")
def test_save_result_updates_existing_row(mock_get_conn, app):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"id": "existing-result-id"}
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with app.app_context():
        result_id = db_service.save_result("mat-1", "summary", "done", content={"title": "Updated"})

    assert result_id == "existing-result-id"
    calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
    assert any("UPDATE results" in sql for sql in calls)


# Decorator order note: bottom @patch → first mock arg, top @patch → second mock arg.
# So mock_get_conn = _get_connection, mock_get_mat = get_material.
@patch("app.services.db_service.get_material")     # top → mock_get_mat (2nd arg)
@patch("app.services.db_service._get_connection")  # bottom → mock_get_conn (1st arg)
def test_get_material_with_results_synthesises_not_requested(mock_get_conn, mock_get_mat, app):
    mock_get_mat.return_value = {
        "id": "mat-1", "filename": "notes.txt", "status": "ready", "error_message": None
    }
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"result_type": "summary", "status": "done",
         "content": '{"title":"t"}', "format_hint": None}
    ]
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with app.app_context():
        result = db_service.get_material_with_results("mat-1", "user-123")

    assert result["material_id"] == "mat-1"
    assert result["results"]["summary"]["status"] == "done"
    assert result["results"]["quiz"]["status"] == "not_requested"
    assert result["results"]["flashcards"]["status"] == "not_requested"


@patch("app.services.db_service.get_material")
def test_get_material_with_results_returns_none_when_missing(mock_get_mat, app):
    mock_get_mat.return_value = None

    with app.app_context():
        result = db_service.get_material_with_results("nonexistent", "user-123")

    assert result is None


@patch("app.services.s3_service._get_client")
def test_upload_file_calls_upload_fileobj(mock_get_client, app):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with app.app_context():
        app.config["S3_BUCKET_NAME"] = "test-bucket"
        s3_service.upload_file(io.BytesIO(b"content"), "uploads/mat-1/notes.txt")

    mock_client.upload_fileobj.assert_called_once()
    call_args = mock_client.upload_fileobj.call_args[0]
    assert call_args[1] == "test-bucket"
    assert call_args[2] == "uploads/mat-1/notes.txt"


@patch("app.services.s3_service._get_client")
def test_get_file_bytes_returns_rewound_bytesio(mock_get_client, app):
    mock_client = MagicMock()
    mock_client.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b"file content"))
    }
    mock_get_client.return_value = mock_client

    with app.app_context():
        app.config["S3_BUCKET_NAME"] = "test-bucket"
        buf = s3_service.get_file_bytes("uploads/mat-1/notes.txt")

    assert buf.read() == b"file content"


def test_extract_text_txt_decodes_utf8(app):
    buf = io.BytesIO("Hello, notes!".encode("utf-8"))
    with app.app_context():
        text = ocr_service.extract_text(buf, "text/plain")
    assert text == "Hello, notes!"


def test_extract_text_markdown_decodes_utf8(app):
    buf = io.BytesIO("# Heading\n\nSome **bold** text.".encode("utf-8"))
    with app.app_context():
        text = ocr_service.extract_text(buf, "text/markdown")
    assert "Heading" in text
    assert "bold" in text


def test_extract_text_markdown_via_octet_stream_fallback(app):
    """octet-stream with file_ext=md should still decode as UTF-8."""
    buf = io.BytesIO("# Notes".encode("utf-8"))
    with app.app_context():
        text = ocr_service.extract_text(buf, "application/octet-stream", "md")
    assert text == "# Notes"


@patch("app.services.ocr_service.Document")
def test_extract_text_docx_by_content_type(mock_document, app):
    mock_para1 = MagicMock()
    mock_para1.text = "First paragraph"
    mock_para2 = MagicMock()
    mock_para2.text = ""
    mock_para3 = MagicMock()
    mock_para3.text = "Third paragraph"
    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]
    mock_document.return_value = mock_doc

    buf = io.BytesIO(b"fake-docx-bytes")
    content_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    with app.app_context():
        text = ocr_service.extract_text(buf, content_type)

    assert text == "First paragraph\nThird paragraph"


@patch("app.services.ocr_service.Document")
def test_extract_text_docx_by_file_ext_fallback(mock_document, app):
    """octet-stream with file_ext=docx should route to docx extraction."""
    mock_para = MagicMock()
    mock_para.text = "Paragraph text"
    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para]
    mock_document.return_value = mock_doc

    buf = io.BytesIO(b"fake-docx-bytes")
    with app.app_context():
        text = ocr_service.extract_text(buf, "application/octet-stream", "docx")

    assert text == "Paragraph text"


@patch("app.services.ocr_service.pdfplumber")
def test_extract_text_pdf_joins_pages(mock_pdfplumber, app):
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page one text"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page two text"
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdfplumber.open.return_value.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdfplumber.open.return_value.__exit__ = MagicMock(return_value=False)

    buf = io.BytesIO(b"%PDF-fake")
    with app.app_context():
        text = ocr_service.extract_text(buf, "application/pdf")

    assert "Page one text" in text
    assert "Page two text" in text


@patch("app.services.ocr_service.boto3")
def test_extract_text_image_calls_textract(mock_boto3, app):
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.detect_document_text.return_value = {
        "Blocks": [
            {"BlockType": "LINE", "Text": "Line one"},
            {"BlockType": "WORD", "Text": "ignored"},
            {"BlockType": "LINE", "Text": "Line two"},
        ]
    }

    buf = io.BytesIO(b"\x89PNG\r\n")
    with app.app_context():
        text = ocr_service.extract_text(buf, "image/png")

    assert text == "Line one\nLine two"
    mock_client.detect_document_text.assert_called_once()
    call_kwargs = mock_client.detect_document_text.call_args[1]
    assert call_kwargs["Document"]["Bytes"] == b"\x89PNG\r\n"


@patch("app.services.ai_service.genai.Client")
def test_generate_summary_returns_parsed_dict(mock_client_class, app):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value = MagicMock(
        text='{"title": "Notes", "key_points": ["a", "b"], "summary": "Short summary"}'
    )

    with app.app_context():
        app.config["GEMINI_API_KEY"] = "test-key"
        result = ai_service.generate("Study text here", "summary")

    assert result["title"] == "Notes"
    mock_client_class.assert_called_once_with(api_key="test-key")


@patch("app.services.ai_service.genai.Client")
def test_generate_quiz_default_uses_mcq_prompt(mock_client_class, app):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value = MagicMock(
        text='{"questions": [{"question": "Q?", "options": ["A","B","C","D"], "correct_index": 0, "explanation": "Because A"}]}'
    )

    with app.app_context():
        app.config["GEMINI_API_KEY"] = "test-key"
        result = ai_service.generate("Text", "quiz")

    prompt = mock_client.models.generate_content.call_args[1]["contents"]
    assert "5 multiple-choice questions" in prompt
    assert result["questions"][0]["question"] == "Q?"


@patch("app.services.ai_service.genai.Client")
def test_generate_quiz_uses_format_hint(mock_client_class, app):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value = MagicMock(text='{"questions": []}')

    with app.app_context():
        app.config["GEMINI_API_KEY"] = "test-key"
        ai_service.generate("Text", "quiz", format_hint="3 true/false questions")

    prompt = mock_client.models.generate_content.call_args[1]["contents"]
    assert "3 true/false questions" in prompt


@patch("app.services.ai_service.genai.Client")
def test_generate_flashcards_returns_parsed_dict(mock_client_class, app):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value = MagicMock(
        text='{"flashcards": [{"front": "Q", "back": "A"}]}'
    )

    with app.app_context():
        app.config["GEMINI_API_KEY"] = "test-key"
        result = ai_service.generate("Text", "flashcards")

    assert result["flashcards"][0]["front"] == "Q"


def test_generate_raises_on_unknown_type(app):
    with app.app_context():
        app.config["GEMINI_API_KEY"] = "test-key"
        with pytest.raises(ValueError, match="Unknown result_type"):
            ai_service.generate("Text", "essay")


@patch("app.services.ai_service.genai.Client")
def test_generate_raises_on_unparseable_json(mock_client_class, app):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value = MagicMock(
        text="```json\n{not valid json}\n```"
    )

    with app.app_context():
        app.config["GEMINI_API_KEY"] = "test-key"
        with pytest.raises(ValueError, match="AI response could not be parsed"):
            ai_service.generate("Study text", "summary")
