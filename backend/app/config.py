import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Loads all configuration from environment variables."""

    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    ENV = os.getenv("FLASK_ENV", "development")
    PORT = int(os.getenv("FLASK_PORT", 5000))

    # AWS General
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

    # S3
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "cloudstudy-uploads-team10")

    # RDS
    RDS_HOST = os.getenv("RDS_HOST", "")
    RDS_PORT = int(os.getenv("RDS_PORT", 3306))
    RDS_DATABASE = os.getenv("RDS_DATABASE", "cloudstudy")
    RDS_USERNAME = os.getenv("RDS_USERNAME", "admin")
    RDS_PASSWORD = os.getenv("RDS_PASSWORD", "")

    # Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Cognito
    COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
    COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")
    COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-1")
    COGNITO_JWKS_URL = (
        f"https://cognito-idp.{os.getenv('COGNITO_REGION', 'us-east-1')}.amazonaws.com"
        f"/{os.getenv('COGNITO_USER_POOL_ID', '')}/.well-known/jwks.json"
    )

    # Allowed upload extensions
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt"}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
