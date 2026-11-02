import io
import shutil
import unittest
from pathlib import Path
from app import create_app
from config import TestConfig
from models.database import db, User, FileItem, StorageAlert
from services.quota_service import QuotaService, QuotaExceededError

class QuotaTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Clean test storage directory
        self.test_dir = Path(self.app.config['LOCAL_STORAGE_DIR'])
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Create user with 10 KB quota (10,240 bytes)
        self.user = User(
            username='quota_tester',
            email='tester@quota.local',
            role='user',
            quota_bytes=10240,
            used_bytes=0,
            is_active=True
        )
        self.user.set_password('Test@123')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_upload_within_quota(self):
        # 4 KB payload (4,096 bytes)
        content = b'A' * 4096
        file_obj = io.BytesIO(content)

        file_record = QuotaService.process_file_upload(
            user_id=self.user.id,
            file_storage=file_obj,
            original_filename='test_doc.txt',
            mime_type='text/plain'
        )

        self.assertIsNotNone(file_record.id)
        self.assertEqual(file_record.size_bytes, 4096)
        
        # Verify user quota updated
        u = User.query.get(self.user.id)
        self.assertEqual(u.used_bytes, 4096)
        self.assertEqual(u.remaining_bytes, 10240 - 4096)
        self.assertEqual(u.usage_percentage, 40.0)

    def test_upload_rejected_when_quota_exceeded(self):
        # User has 10,240 bytes. Attempt to upload 12,000 bytes.
        oversized = b'X' * 12000
        file_obj = io.BytesIO(oversized)

        with self.assertRaises(QuotaExceededError):
            QuotaService.process_file_upload(
                user_id=self.user.id,
                file_storage=file_obj,
                original_filename='huge_file.zip'
            )

        # Verify used_bytes remained 0 and no file record was created
        u = User.query.get(self.user.id)
        self.assertEqual(u.used_bytes, 0)
        self.assertEqual(FileItem.query.filter_by(user_id=self.user.id).count(), 0)

        # Verify StorageAlert logged
        alert = StorageAlert.query.filter_by(user_id=self.user.id, alert_type='QUOTA_EXCEEDED').first()
        self.assertIsNotNone(alert)

    def test_storage_warning_at_80_percent(self):
        # Upload 8,500 bytes (83% of 10,240 quota)
        content = b'B' * 8500
        file_obj = io.BytesIO(content)

        QuotaService.process_file_upload(
            user_id=self.user.id,
            file_storage=file_obj,
            original_filename='warning_trigger.dat'
        )

        u = User.query.get(self.user.id)
        self.assertTrue(u.is_near_quota)
        self.assertGreaterEqual(u.usage_percentage, 80.0)

        # Check that WARNING_80_PERCENT alert was created
        alert = StorageAlert.query.filter_by(user_id=self.user.id, alert_type='WARNING_80_PERCENT').first()
        self.assertIsNotNone(alert)
        self.assertFalse(alert.is_resolved)

    def test_file_deletion_and_quota_refund(self):
        # 1. Upload 5 KB
        content = b'C' * 5120
        file_obj = io.BytesIO(content)
        file_record = QuotaService.process_file_upload(
            user_id=self.user.id,
            file_storage=file_obj,
            original_filename='to_delete.txt'
        )

        u = User.query.get(self.user.id)
        self.assertEqual(u.used_bytes, 5120)

        # 2. Delete file
        QuotaService.process_file_deletion(
            user_id=self.user.id,
            file_id=file_record.id,
            is_admin=False
        )

        # 3. Check quota was restored
        u = User.query.get(self.user.id)
        self.assertEqual(u.used_bytes, 0)
        self.assertEqual(u.remaining_bytes, 10240)
        self.assertIsNone(FileItem.query.get(file_record.id))

    def test_admin_quota_update(self):
        # Admin increases quota from 10KB to 50KB
        admin = User(username='adm', email='adm@quota.local', role='admin')
        admin.set_password('Admin@123')
        db.session.add(admin)
        db.session.commit()

        new_quota = 51200
        QuotaService.update_user_quota(self.user.id, new_quota, admin_id=admin.id)

        u = User.query.get(self.user.id)
        self.assertEqual(u.quota_bytes, 51200)

if __name__ == '__main__':
    unittest.main()
