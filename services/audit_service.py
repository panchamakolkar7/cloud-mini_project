from flask import request
from models.database import db, ActivityLog

class AuditService:
    @staticmethod
    def log_activity(action: str, details: str, user_id: int = None):
        """
        Records an audit activity log entry.
        Never logs passwords or confidential tokens.
        """
        ip = None
        if request:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()

        log_entry = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip
        )
        try:
            db.session.add(log_entry)
            db.session.commit()
        except Exception:
            db.session.rollback()
