import os
from app import create_app
from models.database import db

# Production WSGI application object for Gunicorn
app = create_app()

# Safe database initialization fallback on worker boot
with app.app_context():
    try:
        db.create_all()
        from models.database import User
        if not User.query.filter_by(username='admin').first():
            from init_db import seed_database
            seed_database(app=app)
    except Exception as e:
        # If another worker or process is concurrently initializing, ignore safely
        print(f"[WSGI Init Notice] Handled gracefully: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
