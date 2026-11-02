import io
import shutil
import unittest
from pathlib import Path
from services.local_storage import LocalStorageService
from services.hdfs_storage import HDFSStorageService

class StorageTestCase(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(__file__).resolve().parent / "test_storage_dir"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.local_service = LocalStorageService(self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_local_storage_lifecycle(self):
        # 1. Save file
        sample_data = b"Hello Cloud Computing Mini Project!"
        file_obj = io.BytesIO(sample_data)
        stored_name, path, size = self.local_service.save_file(
            user_id=101,
            file_storage=file_obj,
            filename="my presentation.pdf"
        )
        self.assertTrue(stored_name.endswith("_my_presentation.pdf"))
        self.assertEqual(size, len(sample_data))

        # 2. Retrieve file
        filepath, is_local = self.local_service.get_file_stream(101, stored_name)
        self.assertTrue(is_local)
        self.assertTrue(Path(filepath).exists())
        self.assertEqual(Path(filepath).read_bytes(), sample_data)

        # 3. Path traversal defense
        with self.assertRaises(Exception):
            self.local_service.get_file_stream(101, "../../../etc/passwd")

        # 4. Delete file
        self.assertTrue(self.local_service.delete_file(101, stored_name))
        with self.assertRaises(FileNotFoundError):
            self.local_service.get_file_stream(101, stored_name)

    def test_local_storage_health_check(self):
        health = self.local_service.check_health()
        self.assertEqual(health['status'], 'connected')
        self.assertEqual(health['backend'], 'local')
        self.assertIn('disk_free_human', health['details'])

    def test_hdfs_offline_health_check(self):
        # Point to an offline test address
        hdfs_service = HDFSStorageService(
            namenode_url="http://127.0.0.1:59999",
            hdfs_user="test_hadoop",
            timeout=1
        )
        health = hdfs_service.check_health()
        # Must report disconnected, NEVER falsely claim connected!
        self.assertEqual(health['status'], 'disconnected')
        self.assertEqual(health['backend'], 'hdfs')
        self.assertIn('Cannot connect', health['message'])

if __name__ == '__main__':
    unittest.main()
