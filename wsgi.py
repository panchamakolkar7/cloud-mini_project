import os
from app import create_app
from models.database import db
from init_db import seed_database

# Production WSGI application object for Gunicorn
app = create_app()

with app.app_context():
    # Ensure database schema exists
    db.create_all()
    # Seed default system settings and admin if fresh deployment
    seed_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
