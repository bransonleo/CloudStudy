import json
import uuid
from datetime import datetime

import pymysql
import pymysql.cursors
from flask import current_app


def _get_connection():
    return pymysql.connect(
        host=current_app.config["RDS_HOST"],
        port=int(current_app.config["RDS_PORT"]),
        user=current_app.config["RDS_USERNAME"],
        password=current_app.config["RDS_PASSWORD"],
        database=current_app.config["RDS_DATABASE"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def create_tables():
    """Create materials and results tables if they do not exist."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS materials (
                    id VARCHAR(36) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    s3_key VARCHAR(512) NOT NULL,
                    file_type VARCHAR(10) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    status ENUM('extracting','ready','error') NOT NULL DEFAULT 'extracting',
                    extracted_text LONGTEXT,
                    error_message TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id VARCHAR(36) PRIMARY KEY,
                    material_id VARCHAR(36) NOT NULL,
                    result_type ENUM('summary','quiz','flashcards') NOT NULL,
                    status ENUM('done','error') NOT NULL,
                    content JSON,
                    format_hint TEXT,
                    error_message TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY (material_id) REFERENCES materials(id)
                )
            """)
    finally:
        conn.close()


def create_material(material_id, filename, s3_key, file_type, user_id):
    """Insert a new material row with status='extracting'."""
    now = datetime.utcnow()
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO materials
                   (id, filename, s3_key, file_type, user_id, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, 'extracting', %s, %s)""",
                (material_id, filename, s3_key, file_type, user_id, now, now),
            )
    finally:
        conn.close()


def update_material(material_id, status, extracted_text=None, error_message=None):
    """Update material status, extracted_text, and error_message."""
    now = datetime.utcnow()
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE materials
                   SET status=%s, extracted_text=%s, error_message=%s, updated_at=%s
                   WHERE id=%s""",
                (status, extracted_text, error_message, now, material_id),
            )
    finally:
        conn.close()


def get_material(material_id, user_id=None):
    """Fetch a material row by ID. If user_id is provided, also filter by owner.
    Returns dict or None.

    WARNING: Calling without user_id bypasses ownership filtering.
    Only omit user_id for internal operations (e.g., _run_ocr background thread)
    that are not triggered by user-facing requests.
    """
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "SELECT * FROM materials WHERE id=%s AND user_id=%s",
                    (material_id, user_id),
                )
            else:
                cur.execute("SELECT * FROM materials WHERE id=%s", (material_id,))
            return cur.fetchone()
    finally:
        conn.close()


def save_result(material_id, result_type, status, content=None,
                format_hint=None, error_message=None):
    """Upsert a results row. Returns the result_id."""
    now = datetime.utcnow()
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM results WHERE material_id=%s AND result_type=%s",
                (material_id, result_type),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """UPDATE results
                       SET status=%s, content=%s, format_hint=%s,
                           error_message=%s, updated_at=%s
                       WHERE id=%s""",
                    (
                        status,
                        json.dumps(content) if content else None,
                        format_hint,
                        error_message,
                        now,
                        existing["id"],
                    ),
                )
                return existing["id"]
            else:
                result_id = str(uuid.uuid4())
                cur.execute(
                    """INSERT INTO results
                       (id, material_id, result_type, status, content,
                        format_hint, error_message, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        result_id, material_id, result_type, status,
                        json.dumps(content) if content else None,
                        format_hint, error_message, now, now,
                    ),
                )
                return result_id
    finally:
        conn.close()


def get_material_with_results(material_id, user_id=None):
    """Fetch a material and all its results. Always returns all three result type keys."""
    material = get_material(material_id, user_id)
    if not material:
        return None

    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM results WHERE material_id=%s", (material_id,))
            rows = cur.fetchall()
    finally:
        conn.close()

    results = {
        "summary": {"status": "not_requested"},
        "quiz": {"status": "not_requested"},
        "flashcards": {"status": "not_requested"},
    }
    for row in rows:
        entry = {"status": row["status"]}
        if row["content"]:
            entry["content"] = (
                json.loads(row["content"])
                if isinstance(row["content"], str)
                else row["content"]
            )
        if row.get("format_hint"):
            entry["format_hint"] = row["format_hint"]
        results[row["result_type"]] = entry

    return {
        "material_id": material["id"],
        "filename": material["filename"],
        "status": material["status"],
        "error_message": material.get("error_message"),
        "results": results,
    }
