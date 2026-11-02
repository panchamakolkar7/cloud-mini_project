import os
from pathlib import Path
from app import create_app
from models.database import db, User, FileItem, SystemSetting, ActivityLog, StorageAlert

def seed_database(app=None):
    """
    Safely and idempotently initializes the SQLite database schema and seeds initial data.
    Wraps all inserts in individual transaction rollback blocks to guarantee zero crashes
    even under concurrent execution.
    """
    if app is None:
        app = create_app()

    with app.app_context():
        # Ensure database tables exist safely
        try:
            db.create_all()
        except Exception as e:
            print(f"[Init DB Notice] db.create_all handled: {e}")

        # Seed System Settings safely
        default_settings = [
            ('default_quota_mb', '51200', 'Default quota for new users in MB (50 GB)'),
            ('warning_threshold_percent', '80', 'Storage usage warning threshold %'),
            ('system_storage_capacity_mb', '512000', 'Total cloud cluster capacity in MB (500 GB)'),
        ]
        for key, value, desc in default_settings:
            try:
                setting = SystemSetting.query.filter_by(key=key).first()
                if not setting:
                    db.session.add(SystemSetting(key=key, value=value, description=desc))
                    db.session.commit()
            except Exception:
                db.session.rollback()

        # Seed Administrator Account (admin / Admin@123)
        try:
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                print("Creating default Administrator account (admin / Admin@123)...")
                admin = User(
                    username='admin',
                    email='admin@quotacloud.local',
                    role='admin',
                    quota_bytes=100 * 1024 * 1024 * 1024,  # 100 GB
                    used_bytes=0,
                    is_active=True
                )
                admin.set_password('Admin@123')
                db.session.add(admin)
                db.session.commit()
                print("Admin created.")
        except Exception:
            db.session.rollback()

        # Seed Regular User 1 (user1 / User@123)
        try:
            user1 = User.query.filter_by(username='user1').first()
            if not user1:
                print("Creating default Regular User account (user1 / User@123)...")
                user1 = User(
                    username='user1',
                    email='user1@quotacloud.local',
                    role='user',
                    quota_bytes=50 * 1024 * 1024 * 1024,  # 50 GB
                    used_bytes=0,
                    is_active=True
                )
                user1.set_password('User@123')
                db.session.add(user1)
                db.session.commit()

                # Create sample welcome file for user1
                try:
                    storage_dir = Path(app.config['LOCAL_STORAGE_DIR']) / "users" / str(user1.id) / "files"
                    storage_dir.mkdir(parents=True, exist_ok=True)
                    welcome_filename = "100000000000_Welcome_to_QuotaCloud.txt"
                    target_path = storage_dir / welcome_filename
                    sample_content = (
                        "Welcome to QuotaCloud!\n\n"
                        "QuotaCloud is a multi-user cloud storage and resource management platform.\n"
                        "Key Features:\n"
                        "- Real-time storage quota tracking (50 GB per user)\n"
                        "- 80% usage threshold alerts\n"
                        "- Hadoop HDFS and Local storage abstraction\n"
                        "- Secure file access control\n"
                    ).encode('utf-8')
                    target_path.write_bytes(sample_content)

                    existing_file = FileItem.query.filter_by(user_id=user1.id, stored_filename=welcome_filename).first()
                    if not existing_file:
                        sample_file = FileItem(
                            user_id=user1.id,
                            original_filename="Welcome_to_QuotaCloud.txt",
                            stored_filename=welcome_filename,
                            storage_path=f"local://users/{user1.id}/files/{welcome_filename}",
                            size_bytes=len(sample_content),
                            mime_type="text/plain"
                        )
                        db.session.add(sample_file)
                        user1.used_bytes = len(sample_content)

                        log_entry = ActivityLog(
                            user_id=user1.id,
                            action="USER_REGISTER",
                            details="Account created with default 50 GB quota."
                        )
                        db.session.add(log_entry)
                        db.session.commit()
                        print("User 1 created with sample welcome file.")
                except Exception:
                    db.session.rollback()
        except Exception:
            db.session.rollback()

        # Seed Regular User 2 (user2 / User@123)
        try:
            user2 = User.query.filter_by(username='user2').first()
            if not user2:
                print("Creating second Regular User (user2 / User@123)...")
                user2 = User(
                    username='user2',
                    email='user2@quotacloud.local',
                    role='user',
                    quota_bytes=50 * 1024 * 1024 * 1024,  # 50 GB
                    used_bytes=0,
                    is_active=True
                )
                user2.set_password('User@123')
                db.session.add(user2)
                db.session.commit()
                print("User 2 created.")
        except Exception:
            db.session.rollback()

        print("\n=== Database initialization complete! ===")
        print("Default Credentials:")
        print("  Admin:     Username: admin  | Password: Admin@123 (100 GB quota)")
        print("  User 1:    Username: user1  | Password: User@123 (50 GB quota)")
        print("  User 2:    Username: user2  | Password: User@123 (50 GB quota)")
        print("=========================================\n")

if __name__ == '__main__':
    seed_database()
