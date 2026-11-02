from flask import Blueprint, render_template, current_app
from .auth import admin_required, generate_csrf_token
from models.database import User, ActivityLog, StorageAlert, SystemSetting, format_bytes
from services.storage_service import get_backend_health

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/admin')

@monitoring_bp.route('/monitoring')
@admin_required
def monitoring():
    users = User.query.filter_by(role='user').all()
    
    total_assigned_bytes = sum(u.quota_bytes for u in users)
    total_used_bytes = sum(u.used_bytes for u in users)
    
    system_capacity_mb = int(SystemSetting.get_val('system_storage_capacity_mb', current_app.config['SYSTEM_STORAGE_CAPACITY_MB']))
    system_capacity_bytes = system_capacity_mb * 1024 * 1024
    system_free_bytes = max(0, system_capacity_bytes - total_used_bytes)

    # Users nearing quota (>= 80%)
    near_quota_users = [u for u in users if u.is_near_quota]

    # Backend live health
    backend_health = get_backend_health()

    # Recent storage errors or quota blocks
    storage_errors = ActivityLog.query.filter(
        ActivityLog.action.in_(['UPLOAD_BLOCKED', 'STORAGE_ERROR', 'UNAUTHORIZED_DOWNLOAD_ATTEMPT'])
    ).order_by(ActivityLog.timestamp.desc()).limit(15).all()

    # Storage alerts
    unresolved_alerts = StorageAlert.query.filter_by(is_resolved=False).order_by(StorageAlert.created_at.desc()).all()

    return render_template(
        'monitoring.html',
        total_assigned_human=format_bytes(total_assigned_bytes),
        total_used_human=format_bytes(total_used_bytes),
        system_capacity_human=format_bytes(system_capacity_bytes),
        system_free_human=format_bytes(system_free_bytes),
        total_assigned_bytes=total_assigned_bytes,
        total_used_bytes=total_used_bytes,
        system_capacity_bytes=system_capacity_bytes,
        users=users,
        near_quota_users=near_quota_users,
        backend_health=backend_health,
        storage_errors=storage_errors,
        unresolved_alerts=unresolved_alerts,
        csrf_token=generate_csrf_token()
    )
