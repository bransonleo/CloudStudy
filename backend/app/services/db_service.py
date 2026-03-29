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


def create_material(material_id, filename, s3_key, file_type):
    """Insert a new material row with status='extracting'."""
    now = datetime.utcnow()
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO materials
                   (id, filename, s3_key, file_type, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, 'extracting', %s, %s)""",
                (material_id, filename, s3_key, file_type, now, now),
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
