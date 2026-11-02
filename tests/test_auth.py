import unittest
from app import create_app
from config import TestConfig
from models.database import db, User

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_registration_and_login(self):
        # 1. Register
        resp = self.client.post('/register', data={
            'username': 'tester1',
            'email': 'tester1@example.com',
            'password': 'Password123',
            'confirm_password': 'Password123',
            'csrf_token': ''
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        user = User.query.filter_by(username='tester1').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('Password123'))
        self.assertEqual(user.role, 'user')
        self.assertEqual(user.used_bytes, 0)

        # 2. Login with correct password
        with self.client:
            resp = self.client.post('/login', data={
                'username_or_email': 'tester1',
                'password': 'Password123',
                'csrf_token': ''
            }, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b'tester1', resp.data)

    def test_invalid_password_handling(self):
        # Create user
        user = User(username='bob', email='bob@example.com', role='user', quota_bytes=100000)
        user.set_password('SecretPass')
        db.session.add(user)
        db.session.commit()

        # Login with bad password
        resp = self.client.post('/login', data={
            'username_or_email': 'bob',
            'password': 'WrongPassword!',
            'csrf_token': ''
        }, follow_redirects=True)
        self.assertIn(b'Invalid username/email or password', resp.data)

    def test_deactivated_account_login(self):
        user = User(username='inactive_user', email='inact@example.com', role='user', is_active=False)
        user.set_password('Pass123')
        db.session.add(user)
        db.session.commit()

        resp = self.client.post('/login', data={
            'username_or_email': 'inactive_user',
            'password': 'Pass123',
            'csrf_token': ''
        }, follow_redirects=True)
        self.assertIn(b'deactivated', resp.data)

if __name__ == '__main__':
    unittest.main()
