from flask import current_app
from .local_storage import LocalStorageService
from .hdfs_storage import HDFSStorageService

def get_storage_backend():
    """
    Returns the configured storage service instance according to app configuration.
    """
    backend_type = current_app.config.get("STORAGE_BACKEND", "local").lower().strip()
    
    if backend_type == "hdfs":
        return HDFSStorageService(
            namenode_url=current_app.config.get("HDFS_NAMENODE_URL", "http://localhost:9870"),
            hdfs_user=current_app.config.get("HDFS_USER", "hadoop"),
            root_dir=current_app.config.get("HDFS_ROOT_DIR", "/quotacloud/users"),
            timeout=current_app.config.get("HDFS_TIMEOUT", 5)
        )
    else:
        # Default to local development storage
        return LocalStorageService(
            base_dir=current_app.config["LOCAL_STORAGE_DIR"]
        )

def save_file(user_id: int, file_storage, filename: str):
    backend = get_storage_backend()
    return backend.save_file(user_id, file_storage, filename)

def get_file_stream(user_id: int, stored_filename: str):
    backend = get_storage_backend()
    return backend.get_file_stream(user_id, stored_filename)

def delete_file(user_id: int, stored_filename: str) -> bool:
    backend = get_storage_backend()
    return backend.delete_file(user_id, stored_filename)

def get_backend_health():
    backend = get_storage_backend()
    return backend.check_health()
