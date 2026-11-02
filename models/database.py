import math
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def format_bytes(size_bytes):
    """Utility to format bytes into human-readable B, KB, MB, GB."""
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    
    # Storage quota in bytes (default 50 GB = 53,687,091,200 bytes)
    quota_bytes = db.Column(db.BigInteger, nullable=False, default=53687091200)
    used_bytes = db.Column(db.BigInteger, nullable=False, default=0)
    
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    files = db.relationship('FileItem', backref='owner', lazy=True, cascade="all, delete-orphan")
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)
    alerts = db.relationship('StorageAlert', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def remaining_bytes(self):
        rem = self.quota_bytes - self.used_bytes
        return max(0, rem)

    @property
    def usage_percentage(self):
        if not self.quota_bytes or self.quota_bytes <= 0:
            return 0.0
        pct = (self.used_bytes / self.quota_bytes) * 100.0
        return round(min(100.0, max(0.0, pct)), 1)

    @property
    def readable_quota(self):
        return format_bytes(self.quota_bytes)

    @property
    def readable_used(self):
        return format_bytes(self.used_bytes)

    @property
    def readable_remaining(self):
        return format_bytes(self.remaining_bytes)

    @property
    def is_near_quota(self):
        """Returns True if user has reached or exceeded 80% of storage."""
        return self.usage_percentage >= 80.0

    @property
    def is_quota_full(self):
        """Returns True if user has reached or exceeded 100% of storage."""
        return self.used_bytes >= self.quota_bytes

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "quota_bytes": self.quota_bytes,
            "used_bytes": self.used_bytes,
            "remaining_bytes": self.remaining_bytes,
            "usage_percentage": self.usage_percentage,
            "readable_quota": self.readable_quota,
            "readable_used": self.readable_used,
            "readable_remaining": self.readable_remaining,
            "is_active": self.is_active,
            "is_near_quota": self.is_near_quota,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }


class FileItem(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False, index=True)
    storage_path = db.Column(db.String(500), nullable=False)
    size_bytes = db.Column(db.BigInteger, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False, default='application/octet-stream')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def readable_size(self):
        return format_bytes(self.size_bytes)

    @property
    def file_extension(self):
        if '.' in self.original_filename:
            return self.original_filename.rsplit('.', 1)[1].lower()
        return ''

    @property
    def icon_class(self):
        """Bootstrap icon class based on file extension."""
        ext = self.file_extension
        if ext in ['pdf']:
            return 'bi-file-earmark-pdf text-danger'
        elif ext in ['doc', 'docx', 'txt', 'rtf', 'md']:
            return 'bi-file-earmark-text text-primary'
        elif ext in ['xls', 'xlsx', 'csv']:
            return 'bi-file-earmark-excel text-success'
        elif ext in ['ppt', 'pptx']:
            return 'bi-file-earmark-ppt text-warning'
        elif ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']:
            return 'bi-file-earmark-image text-info'
        elif ext in ['zip', 'rar', 'tar', 'gz', '7z']:
            return 'bi-file-earmark-zip text-secondary'
        elif ext in ['mp3', 'wav', 'ogg']:
            return 'bi-file-earmark-music text-purple'
        elif ext in ['mp4', 'mkv', 'avi', 'mov']:
            return 'bi-file-earmark-play text-danger'
        elif ext in ['py', 'js', 'html', 'css', 'json', 'java', 'c', 'cpp']:
            return 'bi-file-earmark-code text-dark'
        else:
            return 'bi-file-earmark text-muted'

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "storage_path": self.storage_path,
            "size_bytes": self.size_bytes,
            "readable_size": self.readable_size,
            "mime_type": self.mime_type,
            "file_extension": self.file_extension,
            "icon_class": self.icon_class,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "System",
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address or "-",
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }


class StorageAlert(db.Model):
    __tablename__ = 'storage_alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    alert_type = db.Column(db.String(50), nullable=False)  # 'WARNING_80_PERCENT', 'QUOTA_EXCEEDED', 'STORAGE_ERROR'
    message = db.Column(db.Text, nullable=False)
    is_resolved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "Unknown",
            "alert_type": self.alert_type,
            "message": self.message,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    @classmethod
    def get_val(cls, key, default=None):
        item = cls.query.filter_by(key=key).first()
        if item:
            return item.value
        return default

    @classmethod
    def set_val(cls, key, value, description=None):
        item = cls.query.filter_by(key=key).first()
        if not item:
            item = cls(key=key, value=str(value), description=description)
            db.session.add(item)
        else:
            item.value = str(value)
            if description:
                item.description = description
        db.session.commit()
        return item
