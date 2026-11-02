from flask import Blueprint, jsonify, g
from .auth import login_required, admin_required
from models.database import User, StorageAlert
from services.quota_service import QuotaService
from services.storage_service import get_backend_health

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/user/storage-stats')
@login_required
def user_storage_stats():
    return jsonify(QuotaService.get_user_quota_info(g.user.id))

@api_bp.route('/admin/resource-chart-data')
@admin_required
def admin_resource_chart_data():
    users = User.query.filter_by(role='user').all()
    
    usernames = [u.username for u in users]
    used_mb = [round(u.used_bytes / (1024 * 1024), 2) for u in users]
    quota_mb = [round(u.quota_bytes / (1024 * 1024), 2) for u in users]
    remaining_mb = [round(u.remaining_bytes / (1024 * 1024), 2) for u in users]

    total_used_mb = sum(used_mb)
    total_quota_mb = sum(quota_mb)

    return jsonify({
        "usernames": usernames,
        "used_mb": used_mb,
        "quota_mb": quota_mb,
        "remaining_mb": remaining_mb,
        "total_used_mb": round(total_used_mb, 2),
        "total_quota_mb": round(total_quota_mb, 2)
    })

@api_bp.route('/storage/health')
@login_required
def storage_health():
    return jsonify(get_backend_health())

@api_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    query = StorageAlert.query.filter_by(id=alert_id)
    if not g.user.is_admin:
        query = query.filter_by(user_id=g.user.id)
    alert = query.first()
    if alert:
        alert.is_resolved = True
        from models.database import db
        db.session.commit()
        return jsonify({"success": True, "message": "Alert marked as resolved."})
    return jsonify({"success": False, "message": "Alert not found."}), 404
