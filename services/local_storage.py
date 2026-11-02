import os
import shutil
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from .storage_base import BaseStorageService

class LocalStorageService(BaseStorageService):
    """
    Local filesystem storage backend.
    Stores files in a secure directory outside the public web root.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: int) -> Path:
        """Returns isolated user directory path."""
        user_dir = self.base_dir / "users" / str(user_id) / "files"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _generate_safe_stored_filename(self, original_filename: str) -> str:
        safe_name = secure_filename(original_filename)
        if not safe_name:
            safe_name = "unnamed_file"
        unique_prefix = uuid.uuid4().hex[:12]
        return f"{unique_prefix}_{safe_name}"

    def save_file(self, user_id: int, file_storage, filename: str) -> tuple:
        user_dir = self._get_user_dir(user_id)
        stored_filename = self._generate_safe_stored_filename(filename)
        target_path = user_dir / stored_filename

        # Write file and compute exact byte size
        size_bytes = 0
        file_storage.seek(0)
        with open(target_path, "wb") as f:
            while chunk := file_storage.read(65536):
                f.write(chunk)
                size_bytes += len(chunk)

        # Store relative or standard storage path representation
        storage_path = f"local://users/{user_id}/files/{stored_filename}"
        return stored_filename, storage_path, size_bytes

    def get_file_stream(self, user_id: int, stored_filename: str):
        # Prevent path traversal attacks
        safe_name = os.path.basename(stored_filename)
        user_dir = self._get_user_dir(user_id)
        target_path = user_dir / safe_name

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"File not found on local storage: {stored_filename}")

        # Returns the local path, True indicates it can be served directly by send_file
        return str(target_path), True

    def delete_file(self, user_id: int, stored_filename: str) -> bool:
        safe_name = os.path.basename(stored_filename)
        user_dir = self._get_user_dir(user_id)
        target_path = user_dir / safe_name

        if target_path.exists():
            try:
                os.remove(target_path)
                return True
            except OSError as e:
                raise RuntimeError(f"Failed to delete local file: {str(e)}")
        return True

    def check_health(self) -> dict:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            # Check write permission with a test file
            test_file = self.base_dir / ".health_test"
            test_file.write_text("health_check_ok")
            test_file.unlink(missing_ok=True)

            # Get disk usage
            total, used, free = shutil.disk_usage(self.base_dir)

            return {
                "status": "connected",
                "backend": "local",
                "message": "Local file storage is active, healthy, and writable.",
                "details": {
                    "storage_directory": str(self.base_dir),
                    "disk_total_bytes": total,
                    "disk_used_bytes": used,
                    "disk_free_bytes": free,
                    "disk_free_human": f"{round(free / (1024**3), 2)} GB free"
                }
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "backend": "local",
                "message": f"Local storage health check failed: {str(e)}",
                "details": {
                    "storage_directory": str(self.base_dir),
                    "error": str(e)
                }
            }
