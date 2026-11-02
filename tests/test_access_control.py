import io
import shutil
import unittest
from pathlib import Path
from app import create_app
from config import TestConfig
from models.database import db, User, FileItem
from services.quota_service import QuotaService

class AccessControlTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.test_dir = Path(self.app.config['LOCAL_STORAGE_DIR'])
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Create Admin
        self.admin = User(username='admin_boss', email='boss@cloud.local', role='admin', quota_bytes=1000000)
        self.admin.set_password('Admin@123')
        db.session.add(self.admin)

        # Create User A
        self.user_a = User(username='alice', email='alice@cloud.local', role='user', quota_bytes=100000)
        self.user_a.set_password('UserA@123')
        db.session.add(self.user_a)

        # Create User B
        self.user_b = User(username='bob', email='bob@cloud.local', role='user', quota_bytes=100000)
        self.user_b.set_password('UserB@123')
        db.session.add(self.user_b)

        db.session.commit()

        # Alice uploads a private file
        content = b"Alice's Confidential Document"
        file_obj = io.BytesIO(content)
        self.alice_file = QuotaService.process_file_upload(
            user_id=self.user_a.id,
            file_storage=file_obj,
            original_filename='alice_confidential.txt'
        )

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_regular_user_cannot_access_admin_dashboard(self):
        # Login as Bob (regular user)
        with self.client:
            self.client.post('/login', data={
                'username_or_email': 'bob',
                'password': 'UserB@123',
                'csrf_token': ''
            })

            # Attempt to open admin dashboard
            resp = self.client.get('/admin/dashboard', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            # Should have redirected back to user dashboard with access denied flash
            self.assertIn(b'Access denied', resp.data)

    def test_cross_user_file_download_prevention(self):
        # Bob attempts to download Alice's file
        with self.client:
            self.client.post('/login', data={
                'username_or_email': 'bob',
                'password': 'UserB@123',
                'csrf_token': ''
            })

            # Try to download Alice's file ID
            resp = self.client.get(f'/files/{self.alice_file.id}/download')
            # Must return 403 Forbidden!
            self.assertEqual(resp.status_code, 403)

    def test_cross_user_file_delete_prevention(self):
        # Bob attempts to delete Alice's file directly through service
        with self.assertRaises(PermissionError):
            QuotaService.process_file_deletion(
                user_id=self.user_b.id,
                file_id=self.alice_file.id,
                is_admin=False
            )

    def test_owner_can_download_their_own_file(self):
        # Alice downloads her own file
        with self.client:
            self.client.post('/login', data={
                'username_or_email': 'alice',
                'password': 'UserA@123',
                'csrf_token': ''
            })

            resp = self.client.get(f'/files/{self.alice_file.id}/download')
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"Alice's Confidential Document", resp.data)

if __name__ == '__main__':
    unittest.main()
