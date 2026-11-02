import os
from pathlib import Path
from app import create_app
from models.database import db, User, FileItem, SystemSetting, ActivityLog, StorageAlert

def seed_database():
    app = create_app()
    with app.app_context():
        print("Creating SQLite database tables...")
        db.create_all()

        # Seed System Settings
        if not SystemSetting.query.filter_by(key='default_quota_mb').first():
            db.session.add(SystemSetting(key='default_quota_mb', value='51200', description='Default quota for new users in MB (50 GB)'))
        if not SystemSetting.query.filter_by(key='warning_threshold_percent').first():
            db.session.add(SystemSetting(key='warning_threshold_percent', value='80', description='Storage usage warning threshold %'))
        if not SystemSetting.query.filter_by(key='system_storage_capacity_mb').first():
            db.session.add(SystemSetting(key='system_storage_capacity_mb', value='512000', description='Total cloud cluster capacity in MB (500 GB)'))
        db.session.commit()

        # Seed Administrator
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

        # Seed Regular User 1
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

            # Create a sample welcome file for user1 in local storage
            storage_dir = Path(app.config['LOCAL_STORAGE_DIR']) / "users" / str(user1.id) / "files"
            storage_dir.mkdir(parents=True, exist_ok=True)
            welcome_filename = "100000000000_Welcome_to_QuotaCloud.txt"
            target_path = storage_dir / welcome_filename
            sample_content = (
                "Welcome to QuotaCloud!\n\n"
                "QuotaCloud is a multi-user cloud storage and resource management platform.\n"
                "Key Features:\n"
                "- Real-time storage quota tracking\n"
                "- 80% usage threshold alerts\n"
                "- Hadoop HDFS and Local storage abstraction\n"
                "- Secure file access control\n"
            ).encode('utf-8')
            target_path.write_bytes(sample_content)

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

        # Seed Regular User 2 (high storage usage to test 80% warning)
        user2 = User.query.filter_by(username='user2').first()
        if not user2:
            print("Creating second Regular User (user2 / User@123)...")
            user2 = User(
                username='user2',
                email='user2@quotacloud.local',
                role='user',
                quota_bytes=10 * 1024 * 1024 * 1024,  # 10 GB
                used_bytes=0,
                is_active=True
            )
            user2.set_password('User@123')
            db.session.add(user2)
            db.session.commit()
            print("User 2 created.")

        print("\n=== Database initialization complete! ===")
        print("Default Credentials:")
        print("  Admin:     Username: admin  | Password: Admin@123 (100 GB quota)")
        print("  User 1:    Username: user1  | Password: User@123 (50 GB quota)")
        print("  User 2:    Username: user2  | Password: User@123 (10 GB quota)")
        print("=========================================\n")

if __name__ == '__main__':
    seed_database()
