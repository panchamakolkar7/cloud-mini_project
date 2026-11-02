import io
import os
import uuid
import requests
from werkzeug.utils import secure_filename
from .storage_base import BaseStorageService

class HDFSStorageService(BaseStorageService):
    """
    Hadoop Distributed File System (HDFS) storage backend.
    Communicates with Hadoop NameNode & DataNodes via WebHDFS REST API.
    Works seamlessly on both Linux and Windows environments without native Hadoop binaries.
    """

    def __init__(self, namenode_url: str, hdfs_user: str = "hadoop", root_dir: str = "/quotacloud/users", timeout: int = 5):
        self.namenode_url = namenode_url.rstrip("/")
        self.hdfs_user = hdfs_user
        self.root_dir = root_dir.rstrip("/")
        self.timeout = timeout

    def _get_user_hdfs_dir(self, user_id: int) -> str:
        return f"{self.root_dir}/{user_id}/files"

    def _generate_safe_stored_filename(self, original_filename: str) -> str:
        safe_name = secure_filename(original_filename)
        if not safe_name:
            safe_name = "unnamed_file"
        unique_prefix = uuid.uuid4().hex[:12]
        return f"{unique_prefix}_{safe_name}"

    def ensure_hdfs_directory(self, hdfs_path: str):
        """Ensures the directory path exists on HDFS."""
        url = f"{self.namenode_url}/webhdfs/v1{hdfs_path}?op=MKDIRS&user.name={self.hdfs_user}"
        try:
            resp = requests.put(url, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"HDFS directory creation failed for {hdfs_path}: {str(e)}")

    def save_file(self, user_id: int, file_storage, filename: str) -> tuple:
        """
        Saves a file into HDFS via WebHDFS 2-step create protocol.
        Step 1: PUT to NameNode with op=CREATE receives 307 Redirect with DataNode location.
        Step 2: PUT payload to the DataNode URL.
        """
        stored_filename = self._generate_safe_stored_filename(filename)
        user_dir = self._get_user_hdfs_dir(user_id)
        hdfs_target_path = f"{user_dir}/{stored_filename}"

        # Ensure user directory exists
        self.ensure_hdfs_directory(user_dir)

        # Step 1: Request upload location from NameNode
        create_url = f"{self.namenode_url}/webhdfs/v1{hdfs_target_path}?op=CREATE&user.name={self.hdfs_user}&overwrite=true"
        try:
            # allow_redirects=False to inspect the 307 Redirect header
            resp = requests.put(create_url, allow_redirects=False, timeout=self.timeout)
            if resp.status_code != 307:
                raise RuntimeError(f"HDFS NameNode rejected CREATE (status {resp.status_code}): {resp.text}")

            datanode_url = resp.headers.get("Location")
            if not datanode_url:
                raise RuntimeError("HDFS NameNode did not provide a DataNode upload URL.")

            # Step 2: Stream content to DataNode
            file_storage.seek(0)
            data_content = file_storage.read()
            size_bytes = len(data_content)

            upload_resp = requests.put(
                datanode_url,
                data=data_content,
                headers={"Content-Type": "application/octet-stream"},
                timeout=self.timeout * 4
            )
            upload_resp.raise_for_status()

            storage_path = f"hdfs://{hdfs_target_path}"
            return stored_filename, storage_path, size_bytes

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to upload file to HDFS ({self.namenode_url}): {str(e)}")

    def get_file_stream(self, user_id: int, stored_filename: str):
        """
        Downloads a file stream from HDFS via WebHDFS OPEN operation.
        """
        safe_name = os.path.basename(stored_filename)
        user_dir = self._get_user_hdfs_dir(user_id)
        hdfs_target_path = f"{user_dir}/{safe_name}"

        open_url = f"{self.namenode_url}/webhdfs/v1{hdfs_target_path}?op=OPEN&user.name={self.hdfs_user}"
        try:
            resp = requests.get(open_url, stream=True, allow_redirects=True, timeout=self.timeout * 2)
            if resp.status_code == 404:
                raise FileNotFoundError(f"File not found on HDFS: {stored_filename}")
            resp.raise_for_status()

            # Return a BytesIO buffer or streaming generator.
            # Here we wrap the content in BytesIO for Flask send_file compatibility
            file_bytes = io.BytesIO(resp.content)
            return file_bytes, False  # False means it is an in-memory stream, not a local file path
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to read file from HDFS: {str(e)}")

    def delete_file(self, user_id: int, stored_filename: str) -> bool:
        """Deletes a file from HDFS via WebHDFS DELETE operation."""
        safe_name = os.path.basename(stored_filename)
        user_dir = self._get_user_hdfs_dir(user_id)
        hdfs_target_path = f"{user_dir}/{safe_name}"

        delete_url = f"{self.namenode_url}/webhdfs/v1{hdfs_target_path}?op=DELETE&user.name={self.hdfs_user}&recursive=false"
        try:
            resp = requests.delete(delete_url, timeout=self.timeout)
            if resp.status_code in [200, 404]:
                return True
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to delete file from HDFS: {str(e)}")

    def check_health(self) -> dict:
        """
        Actively checks connection to the Hadoop NameNode.
        Never falsely reports HDFS as connected when it is offline.
        """
        test_url = f"{self.namenode_url}/webhdfs/v1/?op=GETHOMEDIRECTORY&user.name={self.hdfs_user}"
        try:
            resp = requests.get(test_url, timeout=self.timeout)
            if resp.status_code in [200, 403]:  # 403 or 200 confirms the WebHDFS daemon is actively responding
                return {
                    "status": "connected",
                    "backend": "hdfs",
                    "message": f"Successfully connected to Hadoop HDFS NameNode at {self.namenode_url}.",
                    "details": {
                        "namenode_url": self.namenode_url,
                        "hdfs_user": self.hdfs_user,
                        "root_dir": self.root_dir,
                        "response_status": resp.status_code
                    }
                }
            else:
                return {
                    "status": "disconnected",
                    "backend": "hdfs",
                    "message": f"HDFS NameNode returned unexpected HTTP status {resp.status_code}.",
                    "details": {
                        "namenode_url": self.namenode_url,
                        "status_code": resp.status_code,
                        "response": resp.text[:200]
                    }
                }
        except requests.ConnectionError:
            return {
                "status": "disconnected",
                "backend": "hdfs",
                "message": f"Cannot connect to Hadoop NameNode at {self.namenode_url}. Connection refused. Ensure Hadoop HDFS daemons (NameNode and DataNode) are running.",
                "details": {
                    "namenode_url": self.namenode_url,
                    "error": "ConnectionRefused"
                }
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "backend": "hdfs",
                "message": f"HDFS connection error: {str(e)}",
                "details": {
                    "namenode_url": self.namenode_url,
                    "error": str(e)
                }
            }
