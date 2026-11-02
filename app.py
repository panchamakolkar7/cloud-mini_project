import os
from flask import Flask, render_template
from config import Config
from models.database import db, format_bytes

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Ensure local storage directory exists
    if app.config.get('STORAGE_BACKEND') == 'local':
        local_dir = app.config.get('LOCAL_STORAGE_DIR')
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

    # Register custom Jinja filters
    @app.template_filter('format_bytes')
    def jinja_format_bytes(size):
        return format_bytes(size)

    # Context processors
    @app.context_processor
    def inject_global_vars():
        return {
            'STORAGE_BACKEND': app.config.get('STORAGE_BACKEND', 'local'),
            'MAX_CONTENT_LENGTH_MB': app.config.get('MAX_CONTENT_LENGTH_MB', 100)
        }

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.files import files_bp
    from routes.admin import admin_bp
    from routes.monitoring import monitoring_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(api_bp)

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('error.html', error_code=403, error_title="Forbidden", error_message="You do not have permission to access this resource."), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error_code=404, error_title="Page Not Found", error_message="The requested page or file does not exist."), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        max_mb = app.config.get('MAX_CONTENT_LENGTH_MB', 100)
        return render_template('error.html', error_code=413, error_title="File Too Large", error_message=f"The uploaded file exceeds the maximum allowed server limit of {max_mb} MB."), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('error.html', error_code=500, error_title="Server Error", error_message="An unexpected server error occurred. Please try again later."), 500

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5000, debug=True)
