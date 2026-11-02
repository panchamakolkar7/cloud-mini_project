from .auth import auth_bp
from .user import user_bp
from .files import files_bp
from .admin import admin_bp
from .monitoring import monitoring_bp
from .api import api_bp

__all__ = ['auth_bp', 'user_bp', 'files_bp', 'admin_bp', 'monitoring_bp', 'api_bp']
