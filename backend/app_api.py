from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.models.db_client import init_db
from backend.api.shouts import shouts_bp
from backend.api.chat import chat_bp
from backend.api.utils import utils_bp
from backend.api.admin import admin_bp
import logging

def create_app():
    """Application factory"""

    # Validate configuration
    Config.validate()

    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(Config)

    # Setup CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if Config.DEBUG else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize PostgreSQL connection pool
    init_db()

    # Register blueprints
    app.register_blueprint(shouts_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(utils_bp)
    app.register_blueprint(admin_bp)

    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'service': 'BurnAfterIt API',
            'version': '2.0',
            'endpoints': {
                'shouts': '/api/shouts',
                'chat': '/api/chat',
                'utils': '/api/utils',
                'health': '/api/utils/health'
            }
        })

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': 'File too large'}), 413

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
