import io

import boto3
import pdfplumber
from docx import Document
from flask import current_app


def extract_text(file_bytes, content_type, file_ext=""):
    """Extract text from a BytesIO buffer. Routes by content_type with
    file_ext as fallback for ambiguous MIME types (e.g. application/octet-stream)."""
    if "pdf" in content_type:
        return _extract_pdf(file_bytes)
    elif content_type in ("image/png", "image/jpeg", "image/jpg"):
        return _extract_image(file_bytes)
    elif (
        "wordprocessingml" in content_type
        or "officedocument" in content_type
        or file_ext == "docx"
    ):
        return _extract_docx(file_bytes)
    else:
        return file_bytes.read().decode("utf-8")


def _extract_pdf(file_bytes):
    text_parts = []
    with pdfplumber.open(file_bytes) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def _extract_image(file_bytes):
    client = boto3.client("textract", region_name=current_app.config["AWS_REGION"])
    response = client.detect_document_text(Document={"Bytes": file_bytes.read()})
    lines = [
        block["Text"]
        for block in response["Blocks"]
        if block["BlockType"] == "LINE"
    ]
    return "\n".join(lines)


def _extract_docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes.read()))
    return "\n".join(p.text for p in doc.paragraphs if p.text)
