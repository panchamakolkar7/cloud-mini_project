import threading
from models.database import db, User, FileItem, format_bytes
from services.alert_service import AlertService
from services.audit_service import AuditService
from services.storage_service import save_file as storage_save_file, delete_file as storage_delete_file

# Lock dictionary for thread-safe concurrent uploads per user
_user_locks = {}
_global_lock = threading.Lock()

def _get_user_lock(user_id: int) -> threading.Lock:
    with _global_lock:
        if user_id not in _user_locks:
            _user_locks[user_id] = threading.Lock()
        return _user_locks[user_id]


class QuotaExceededError(Exception):
    def __init__(self, message, remaining_bytes=0, file_size=0):
        super().__init__(message)
        self.remaining_bytes = remaining_bytes
        self.file_size = file_size


class QuotaService:
    @staticmethod
    def get_user_quota_info(user_id: int) -> dict:
        user = User.query.get(user_id)
        if not user:
            return {}
        return {
            "quota_bytes": user.quota_bytes,
            "used_bytes": user.used_bytes,
            "remaining_bytes": user.remaining_bytes,
            "usage_percentage": user.usage_percentage,
            "readable_quota": user.readable_quota,
            "readable_used": user.readable_used,
            "readable_remaining": user.readable_remaining,
            "is_near_quota": user.is_near_quota,
            "is_quota_full": user.is_quota_full
        }

    @staticmethod
    def process_file_upload(user_id: int, file_storage, original_filename: str, mime_type: str = None) -> FileItem:
        """
        Thread-safe, transaction-atomic upload processing:
        1. Validates file and computes stream size
        2. Acquires per-user lock
        3. Verifies remaining quota on fresh database state
        4. Rejects if file_size > remaining_bytes
        5. Saves to storage backend (Local or HDFS)
        6. Updates used_bytes and commits FileItem record
        7. Triggers quota alerts if >= 80%
        """
        if not original_filename:
            raise ValueError("No file selected or empty filename.")

        # Determine file size by reading stream into memory or seeking
        file_storage.seek(0, 2)  # seek to end
        file_size = file_storage.tell()
        file_storage.seek(0)     # reset to beginning

        if file_size <= 0:
            raise ValueError("File is empty (0 bytes). Cannot upload empty files.")

        user_lock = _get_user_lock(user_id)
        with user_lock:
            # Query fresh user state inside user lock
            user = User.query.filter_by(id=user_id).with_for_update().first() if db.engine.name != 'sqlite' else User.query.get(user_id)
            if not user:
                raise ValueError("User not found.")

            if not user.is_active:
                raise PermissionError("Your user account is deactivated. Uploads are disabled.")

            remaining = user.remaining_bytes
            if file_size > remaining:
                file_size_human = format_bytes(file_size)
                remaining_human = format_bytes(remaining)
                AlertService.log_quota_exceeded_alert(user_id, original_filename, file_size_human, remaining_human)
                AuditService.log_activity(
                    action="UPLOAD_BLOCKED",
                    details=f"Upload of '{original_filename}' ({file_size_human}) blocked: exceeded remaining quota ({remaining_human})",
                    user_id=user_id
                )
                raise QuotaExceededError(
                    f"Upload rejected: File size ({file_size_human}) exceeds your remaining quota ({remaining_human}).",
                    remaining_bytes=remaining,
                    file_size=file_size
                )

            # Tentatively save to storage backend
            stored_filename = None
            try:
                stored_filename, storage_path, actual_size = storage_save_file(user_id, file_storage, original_filename)
                
                # Check actual size written matches or within quota
                if actual_size > remaining:
                    # Clean up saved file immediately
                    storage_delete_file(user_id, stored_filename)
                    raise QuotaExceededError("Actual uploaded size exceeded remaining quota.")

                # Create FileItem record
                file_record = FileItem(
                    user_id=user_id,
                    original_filename=original_filename,
                    stored_filename=stored_filename,
                    storage_path=storage_path,
                    size_bytes=actual_size,
                    mime_type=mime_type or "application/octet-stream"
                )
                db.session.add(file_record)

                # Atomically update user's used_bytes
                user.used_bytes = user.used_bytes + actual_size
                db.session.commit()

                # Audit log
                AuditService.log_activity(
                    action="FILE_UPLOAD",
                    details=f"Uploaded '{original_filename}' ({format_bytes(actual_size)}) to {storage_path}",
                    user_id=user_id
                )

                # Check and trigger storage alerts (e.g. 80% warning)
                AlertService.check_user_quota_alerts(user_id)

                return file_record

            except Exception as e:
                db.session.rollback()
                # Clean up stored file if already written
                if stored_filename:
                    try:
                        storage_delete_file(user_id, stored_filename)
                    except Exception:
                        pass
                AlertService.log_storage_error_alert(user_id, f"Upload error: {str(e)}")
                raise

    @staticmethod
    def process_file_deletion(user_id: int, file_id: int, is_admin: bool = False) -> bool:
        """
        Safely deletes a file from storage and updates quota usage.
        Prevents unauthorized users from deleting another user's file.
        """
        user_lock = _get_user_lock(user_id)
        with user_lock:
            file_record = FileItem.query.get(file_id)
            if not file_record:
                raise FileNotFoundError("File not found.")

            # Access control check
            if file_record.user_id != user_id and not is_admin:
                AuditService.log_activity(
                    action="UNAUTHORIZED_DELETE_ATTEMPT",
                    details=f"User {user_id} attempted to delete file ID {file_id} belonging to user {file_record.user_id}",
                    user_id=user_id
                )
                raise PermissionError("Access denied: You do not have permission to delete this file.")

            file_owner = User.query.get(file_record.user_id)
            file_size = file_record.size_bytes
            stored_filename = file_record.stored_filename
            original_filename = file_record.original_filename

            # Delete from storage backend
            storage_delete_file(file_record.user_id, stored_filename)

            # Update database
            db.session.delete(file_record)
            if file_owner:
                # Recalculate and prevent negative usage values
                file_owner.used_bytes = max(0, file_owner.used_bytes - file_size)

            db.session.commit()

            # Audit log
            AuditService.log_activity(
                action="FILE_DELETE",
                details=f"Deleted '{original_filename}' ({format_bytes(file_size)})",
                user_id=user_id
            )

            # Re-evaluate quota alerts (may resolve 80% warning if usage dropped)
            if file_owner:
                AlertService.check_user_quota_alerts(file_owner.id)

            return True

    @staticmethod
    def update_user_quota(user_id: int, new_quota_bytes: int, admin_id: int) -> User:
        """
        Admin updates a user's quota.
        """
        if new_quota_bytes <= 0:
            raise ValueError("Quota must be a positive number of bytes.")

        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found.")

        old_quota_str = user.readable_quota
        user.quota_bytes = new_quota_bytes
        db.session.commit()

        new_quota_str = user.readable_quota
        AuditService.log_activity(
            action="QUOTA_CHANGE",
            details=f"Updated quota for user '{user.username}' from {old_quota_str} to {new_quota_str}",
            user_id=admin_id
        )

        AlertService.check_user_quota_alerts(user.id)
        return user
