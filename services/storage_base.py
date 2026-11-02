from abc import ABC, abstractmethod

class BaseStorageService(ABC):
    """
    Abstract Base Class for QuotaCloud Storage Backends.
    Allows seamless switching between Local Filesystem and Hadoop HDFS.
    """

    @abstractmethod
    def save_file(self, user_id: int, file_storage, filename: str) -> tuple:
        """
        Saves an uploaded file to the storage backend.
        Returns:
            tuple: (stored_filename: str, storage_path: str, size_bytes: int)
        Raises:
            Exception: If saving fails
        """
        pass

    @abstractmethod
    def get_file_stream(self, user_id: int, stored_filename: str):
        """
        Retrieves a file from the storage backend.
        Returns:
            tuple: (file_stream_or_path, is_local_path: bool)
        Raises:
            FileNotFoundError: If the file does not exist
        """
        pass

    @abstractmethod
    def delete_file(self, user_id: int, stored_filename: str) -> bool:
        """
        Deletes a file from the storage backend.
        Returns:
            bool: True if deleted or already gone
        """
        pass

    @abstractmethod
    def check_health(self) -> dict:
        """
        Checks connection status to the storage backend.
        Returns:
            dict: {
                "status": "connected" | "disconnected",
                "backend": "local" | "hdfs",
                "message": str,
                "details": dict
            }
        """
        pass
