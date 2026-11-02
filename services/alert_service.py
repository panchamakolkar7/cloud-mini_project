from datetime import datetime
from models.database import db, StorageAlert, User

class AlertService:
    @staticmethod
    def check_user_quota_alerts(user_id: int):
        """
        Evaluates user's current storage usage and triggers or resolves alerts.
        """
        user = User.query.get(user_id)
        if not user:
            return

        pct = user.usage_percentage
        
        # 1. Check for >= 80% warning
        if pct >= 80.0:
            existing = StorageAlert.query.filter_by(
                user_id=user_id,
                alert_type='WARNING_80_PERCENT',
                is_resolved=False
            ).first()

            if not existing:
                alert = StorageAlert(
                    user_id=user_id,
                    alert_type='WARNING_80_PERCENT',
                    message=f"Storage Warning: You have utilized {pct}% of your allocated {user.readable_quota} quota.",
                    is_resolved=False
                )
                db.session.add(alert)
                db.session.commit()
        else:
            # If usage dropped below 80%, resolve pending 80% warning alerts
            existing = StorageAlert.query.filter_by(
                user_id=user_id,
                alert_type='WARNING_80_PERCENT',
                is_resolved=False
            ).all()
            for a in existing:
                a.is_resolved = True
            if existing:
                db.session.commit()

    @staticmethod
    def log_quota_exceeded_alert(user_id: int, attempted_file_name: str, file_size_readable: str, remaining_readable: str):
        alert = StorageAlert(
            user_id=user_id,
            alert_type='QUOTA_EXCEEDED',
            message=f"Upload Blocked: '{attempted_file_name}' ({file_size_readable}) exceeded your remaining quota of {remaining_readable}.",
            is_resolved=False
        )
        db.session.add(alert)
        db.session.commit()

    @staticmethod
    def log_storage_error_alert(user_id: int, message: str):
        alert = StorageAlert(
            user_id=user_id,
            alert_type='STORAGE_ERROR',
            message=f"Storage system error: {message}",
            is_resolved=False
        )
        db.session.add(alert)
        db.session.commit()

    @staticmethod
    def resolve_alert(alert_id: int, user_id: int = None):
        query = StorageAlert.query.filter_by(id=alert_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        alert = query.first()
        if alert:
            alert.is_resolved = True
            db.session.commit()
            return True
        return False
