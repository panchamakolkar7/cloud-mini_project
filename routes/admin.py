import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, current_app
from .auth import admin_required, validate_csrf, generate_csrf_token
from models.database import db, User, FileItem, ActivityLog, StorageAlert, SystemSetting, format_bytes
from services.quota_service import QuotaService
from services.audit_service import AuditService
from services.storage_service import get_backend_health, delete_file as storage_delete_file

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_users = User.query.filter_by(role='user').count()
    total_files = FileItem.query.count()
    
    # Storage calculations across users
    users = User.query.filter_by(role='user').all()
    total_assigned_quota = sum(u.quota_bytes for u in users)
    total_storage_used = sum(u.used_bytes for u in users)
    
    # System capacity
    system_capacity_mb = int(SystemSetting.get_val('system_storage_capacity_mb', current_app.config['SYSTEM_STORAGE_CAPACITY_MB']))
    system_capacity_bytes = system_capacity_mb * 1024 * 1024
    total_available_storage = max(0, system_capacity_bytes - total_storage_used)
    
    system_usage_percent = round((total_storage_used / system_capacity_bytes) * 100, 1) if system_capacity_bytes > 0 else 0
    quota_allocation_percent = round((total_assigned_quota / system_capacity_bytes) * 100, 1) if system_capacity_bytes > 0 else 0

    # Recent activities
    recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(8).all()

    # Active alerts
    active_alerts = StorageAlert.query.filter_by(is_resolved=False).order_by(StorageAlert.created_at.desc()).limit(8).all()

    # Backend status
    backend_health = get_backend_health()

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_files=total_files,
        total_assigned_quota=format_bytes(total_assigned_quota),
        total_storage_used=format_bytes(total_storage_used),
        total_available_storage=format_bytes(total_available_storage),
        system_capacity=format_bytes(system_capacity_bytes),
        total_storage_used_bytes=total_storage_used,
        system_capacity_bytes=system_capacity_bytes,
        system_usage_percent=system_usage_percent,
        quota_allocation_percent=quota_allocation_percent,
        recent_activities=recent_activities,
        active_alerts=active_alerts,
        backend_health=backend_health,
        csrf_token=generate_csrf_token()
    )

@admin_bp.route('/users')
@admin_required
def users_list():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all')

    query = User.query

    if search_query:
        query = query.filter((User.username.ilike(f'%{search_query}%')) | (User.email.ilike(f'%{search_query}%')))

    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)

    users = query.order_by(User.created_at.desc()).all()
    default_quota_mb = int(SystemSetting.get_val('default_quota_mb', current_app.config['DEFAULT_USER_QUOTA_MB']))

    return render_template(
        'users.html',
        users=users,
        search_query=search_query,
        status_filter=status_filter,
        default_quota_mb=default_quota_mb,
        csrf_token=generate_csrf_token()
    )

@admin_bp.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    if not validate_csrf():
        flash("CSRF validation failed.", "danger")
        return redirect(url_for('admin.users_list'))

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    role = request.form.get('role', 'user')
    quota_mb = request.form.get('quota_mb', type=int)

    if not username or not email or not password:
        flash("Username, email, and password are required.", "danger")
        return redirect(url_for('admin.users_list'))

    if not re.match(r'^[a-zA-Z0-9_-]{3,30}$', username):
        flash("Invalid username format. Must be 3-30 letters/numbers/-/_.", "danger")
        return redirect(url_for('admin.users_list'))

    if User.query.filter_by(username=username).first():
        flash(f"User with username '{username}' already exists.", "danger")
        return redirect(url_for('admin.users_list'))

    if User.query.filter_by(email=email).first():
        flash(f"User with email '{email}' already exists.", "danger")
        return redirect(url_for('admin.users_list'))

    if not quota_mb or quota_mb <= 0:
        quota_mb = int(SystemSetting.get_val('default_quota_mb', current_app.config['DEFAULT_USER_QUOTA_MB']))

    new_user = User(
        username=username,
        email=email,
        role=role if role in ['admin', 'user'] else 'user',
        quota_bytes=quota_mb * 1024 * 1024,
        used_bytes=0,
        is_active=True
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    AuditService.log_activity(
        action="USER_CREATE",
        details=f"Admin created user '{username}' (Role: {new_user.role}, Quota: {quota_mb} MB).",
        user_id=g.user.id
    )

    flash(f"User '{username}' created successfully.", "success")
    return redirect(url_for('admin.users_list'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    if not validate_csrf():
        flash("CSRF validation failed.", "danger")
        return redirect(url_for('admin.users_list'))

    user = User.query.get_or_404(user_id)
    email = request.form.get('email', '').strip().lower()
    quota_mb = request.form.get('quota_mb', type=int)
    new_password = request.form.get('password', '').strip()

    if email and email != user.email:
        if User.query.filter_by(email=email).first():
            flash("That email is already in use by another user.", "danger")
            return redirect(url_for('admin.users_list'))
        user.email = email

    if quota_mb and quota_mb > 0:
        new_quota_bytes = quota_mb * 1024 * 1024
        QuotaService.update_user_quota(user.id, new_quota_bytes, admin_id=g.user.id)

    if new_password:
        if len(new_password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for('admin.users_list'))
        user.set_password(new_password)
        AuditService.log_activity(
            action="ADMIN_PASSWORD_RESET",
            details=f"Admin reset password for user '{user.username}'.",
            user_id=g.user.id
        )

    db.session.commit()
    flash(f"User '{user.username}' updated successfully.", "success")
    return redirect(url_for('admin.users_list'))

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    if not validate_csrf():
        flash("CSRF validation failed.", "danger")
        return redirect(url_for('admin.users_list'))

    user = User.query.get_or_404(user_id)

    # Prevent admin from deactivating themselves
    if user.id == g.user.id:
        flash("You cannot deactivate your own administrative account.", "warning")
        return redirect(url_for('admin.users_list'))

    user.is_active = not user.is_active
    status_str = "activated" if user.is_active else "deactivated"
    db.session.commit()

    AuditService.log_activity(
        action="USER_STATUS_CHANGE",
        details=f"Admin {status_str} user account '{user.username}'.",
        user_id=g.user.id
    )

    flash(f"User '{user.username}' account has been {status_str}.", "info")
    return redirect(url_for('admin.users_list'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    if not validate_csrf():
        flash("CSRF validation failed.", "danger")
        return redirect(url_for('admin.users_list'))

    user = User.query.get_or_404(user_id)

    if user.id == g.user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for('admin.users_list'))

    # Clean up all user files from storage backend
    username = user.username
    user_files = FileItem.query.filter_by(user_id=user.id).all()
    for f in user_files:
        try:
            storage_delete_file(user.id, f.stored_filename)
        except Exception:
            pass

    # Delete user and cascade in database
    db.session.delete(user)
    db.session.commit()

    AuditService.log_activity(
        action="USER_DELETE",
        details=f"Admin deleted user '{username}' and purged {len(user_files)} storage files.",
        user_id=g.user.id
    )

    flash(f"User '{username}' and associated files have been permanently removed.", "info")
    return redirect(url_for('admin.users_list'))

@admin_bp.route('/logs')
@admin_required
def activity_logs():
    action_filter = request.args.get('action', 'all')
    search_query = request.args.get('q', '').strip()

    query = ActivityLog.query

    if action_filter != 'all':
        query = query.filter_by(action=action_filter)

    if search_query:
        query = query.filter((ActivityLog.details.ilike(f'%{search_query}%')) | (ActivityLog.ip_address.ilike(f'%{search_query}%')))

    logs = query.order_by(ActivityLog.timestamp.desc()).limit(200).all()

    # Get distinct actions for filtering
    distinct_actions = [r[0] for r in db.session.query(ActivityLog.action).distinct().all()]

    return render_template(
        'activity_logs.html',
        logs=logs,
        action_filter=action_filter,
        search_query=search_query,
        distinct_actions=distinct_actions,
        csrf_token=generate_csrf_token()
    )

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        if not validate_csrf():
            flash("CSRF validation failed.", "danger")
            return redirect(url_for('admin.settings'))

        default_quota_mb = request.form.get('default_quota_mb', type=int)
        warning_threshold = request.form.get('warning_threshold_percent', type=float)
        system_capacity_mb = request.form.get('system_capacity_mb', type=int)

        if default_quota_mb and default_quota_mb > 0:
            SystemSetting.set_val('default_quota_mb', default_quota_mb, "Default quota assigned to new users in MB")

        if warning_threshold and 10 <= warning_threshold <= 95:
            SystemSetting.set_val('warning_threshold_percent', warning_threshold, "Storage usage percentage threshold for alerts")

        if system_capacity_mb and system_capacity_mb > 0:
            SystemSetting.set_val('system_storage_capacity_mb', system_capacity_mb, "Total theoretical system cloud storage capacity in MB")

        AuditService.log_activity(
            action="SETTINGS_UPDATE",
            details=f"Admin updated system settings: default_quota={default_quota_mb}MB, warning_threshold={warning_threshold}%, capacity={system_capacity_mb}MB",
            user_id=g.user.id
        )

        flash("Settings updated successfully.", "success")
        return redirect(url_for('admin.settings'))

    current_settings = {
        "default_quota_mb": int(SystemSetting.get_val('default_quota_mb', current_app.config['DEFAULT_USER_QUOTA_MB'])),
        "warning_threshold_percent": float(SystemSetting.get_val('warning_threshold_percent', current_app.config['STORAGE_WARNING_THRESHOLD_PERCENT'])),
        "system_capacity_mb": int(SystemSetting.get_val('system_storage_capacity_mb', current_app.config['SYSTEM_STORAGE_CAPACITY_MB'])),
        "storage_backend": current_app.config['STORAGE_BACKEND'],
        "local_storage_dir": str(current_app.config['LOCAL_STORAGE_DIR']),
        "hdfs_namenode_url": current_app.config['HDFS_NAMENODE_URL'],
        "hdfs_user": current_app.config['HDFS_USER'],
        "hdfs_root_dir": current_app.config['HDFS_ROOT_DIR']
    }

    backend_health = get_backend_health()

    return render_template(
        'settings.html',
        settings=current_settings,
        backend_health=backend_health,
        csrf_token=generate_csrf_token()
    )
