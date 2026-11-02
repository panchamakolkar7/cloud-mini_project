from flask import Blueprint, render_template, redirect, url_for, flash, g, request
from .auth import login_required, validate_csrf, generate_csrf_token
from models.database import db, FileItem, StorageAlert, ActivityLog
from services.storage_service import get_backend_health

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def index():
    if g.user:
        return redirect(url_for('admin.dashboard' if g.user.is_admin else 'user.dashboard'))
    return redirect(url_for('auth.login'))

@user_bp.route('/dashboard')
@login_required
def dashboard():
    # If admin accesses /dashboard, allow viewing user view or redirect
    user = g.user
    
    # Files statistics
    files_count = FileItem.query.filter_by(user_id=user.id).count()
    recent_files = FileItem.query.filter_by(user_id=user.id).order_by(FileItem.created_at.desc()).limit(5).all()
    
    # Active storage alerts
    active_alerts = StorageAlert.query.filter_by(user_id=user.id, is_resolved=False).order_by(StorageAlert.created_at.desc()).all()
    
    # Recent user activity
    recent_activities = ActivityLog.query.filter_by(user_id=user.id).order_by(ActivityLog.timestamp.desc()).limit(6).all()
    
    # Backend health
    backend_health = get_backend_health()

    return render_template(
        'dashboard.html',
        user=user,
        files_count=files_count,
        recent_files=recent_files,
        active_alerts=active_alerts,
        recent_activities=recent_activities,
        backend_health=backend_health,
        csrf_token=generate_csrf_token()
    )

@user_bp.route('/alerts/<int:alert_id>/dismiss', methods=['POST'])
@login_required
def dismiss_alert(alert_id):
    if not validate_csrf():
        flash("CSRF token verification failed.", "danger")
        return redirect(url_for('user.dashboard'))

    alert = StorageAlert.query.filter_by(id=alert_id, user_id=g.user.id).first()
    if alert:
        alert.is_resolved = True
        db.session.commit()
        flash("Notification dismissed.", "info")
    return redirect(request.referrer or url_for('user.dashboard'))
