import os
from app import create_app
from models.database import db
from init_db import seed_database

def main():
    app = create_app()

    # Automatically initialize tables and seed defaults if first run
    db_path = app.config['BASE_DIR'] / "quotacloud.db"
    if not db_path.exists():
        print("[QuotaCloud] Initializing fresh database and seeding demo users...")
        seed_database()
    else:
        with app.app_context():
            db.create_all()

    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "127.0.0.1")

    print("\n" + "=" * 60)
    print("   QuotaCloud — Cloud Storage & Resource Management SaaS")
    print("=" * 60)
    print(f" * Server running on: http://{host}:{port}/")
    print(f" * Active Storage Mode: {app.config['STORAGE_BACKEND'].upper()}")
    print(" * Admin login:  username: admin | password: Admin@123")
    print(" * User login:   username: user1 | password: User@123")
    print("=" * 60 + "\n")

    app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    main()
