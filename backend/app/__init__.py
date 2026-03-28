from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config


def create_app():
    """Application factory — creates and configures the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS: allow frontend dev server
    CORS(app)

    # Register blueprints
    from app.routes.health import health_bp

    app.register_blueprint(health_bp, url_prefix="/api")

    from app.routes.upload import upload_bp

    app.register_blueprint(upload_bp, url_prefix="/api")

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
