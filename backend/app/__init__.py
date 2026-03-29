from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config


def create_app(test_config=None):
    """Application factory — creates and configures the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # CORS: allow frontend dev server
    CORS(app)

    # Register blueprints
    from app.routes.health import health_bp

    app.register_blueprint(health_bp, url_prefix="/api")

    from app.routes.upload import upload_bp

    app.register_blueprint(upload_bp, url_prefix="/api")

    from app.routes.generate import generate_bp

    app.register_blueprint(generate_bp, url_prefix="/api")

    # Create database tables on startup (unless testing)
    if not app.config.get("TESTING"):
        from app.services import db_service
        db_service.create_tables()

    # Global error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "status": 404}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large", "status": 413}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error", "status": 500}), 500

    return app
