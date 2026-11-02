import secrets
import re
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app
from models.database import db, User, SystemSetting
from services.audit_service import AuditService

auth_bp = Blueprint('auth', __name__)

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']

def validate_csrf():
    if current_app.config.get('TESTING', False):
        return True
    token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
    expected = session.get('_csrf_token')
    if not expected or not token or not secrets.compare_digest(token, expected):
        return False
    return True

@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)
        if g.user and not g.user.is_active:
            # If account was deactivated while logged in
            session.clear()
            g.user = None

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in with an administrator account.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        if not g.user.is_admin:
            flash("Access denied. Administrator privileges required.", "danger")
            return redirect(url_for('user.dashboard'))
        return view(**kwargs)
    return wrapped_view

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None:
        return redirect(url_for('admin.dashboard' if g.user.is_admin else 'user.dashboard'))

    if request.method == 'POST':
        if not validate_csrf():
            flash("Security check failed (CSRF token invalid). Please try again.", "danger")
            return render_template('login.html', csrf_token=generate_csrf_token())

        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')

        if not username_or_email or not password:
            flash("Please provide both username/email and password.", "danger")
            return render_template('login.html', csrf_token=generate_csrf_token())

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email.lower())
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                AuditService.log_activity(
                    action="LOGIN_BLOCKED",
                    details=f"Deactivated user '{user.username}' attempted to log in.",
                    user_id=user.id
                )
                flash("Your account has been deactivated. Please contact an administrator.", "danger")
                return render_template('login.html', csrf_token=generate_csrf_token())

            # Set session
            session.clear()
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            generate_csrf_token()

            AuditService.log_activity(
                action="LOGIN_SUCCESS",
                details=f"User '{user.username}' logged in successfully.",
                user_id=user.id
            )

            flash(f"Welcome back, {user.username}!", "success")
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('admin.dashboard' if user.is_admin else 'user.dashboard'))
        else:
            AuditService.log_activity(
                action="LOGIN_FAILED",
                details=f"Failed login attempt for identifier '{username_or_email}'."
            )
            flash("Invalid username/email or password.", "danger")

    return render_template('login.html', csrf_token=generate_csrf_token())

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.user is not None:
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        if not validate_csrf():
            flash("Security check failed (CSRF token invalid).", "danger")
            return render_template('register.html', csrf_token=generate_csrf_token())

        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template('register.html', csrf_token=generate_csrf_token())

        if not re.match(r'^[a-zA-Z0-9_-]{3,30}$', username):
            flash("Username must be 3-30 characters long and contain only letters, numbers, underscores, and hyphens.", "danger")
            return render_template('register.html', csrf_token=generate_csrf_token())

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash("Please provide a valid email address.", "danger")
            return render_template('register.html', csrf_token=generate_csrf_token())

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html', csrf_token=generate_csrf_token())

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', csrf_token=generate_csrf_token())

        if User.query.filter_by(username=username).first():
            flash("That username is already taken. Please choose another.", "danger")
            return render_template('register.html', csrf_token=generate_csrf_token())

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template('register.html', csrf_token=generate_csrf_token())

        # Determine default quota from SystemSetting or config (default 51200 MB = 50 GB)
        default_quota_mb = int(SystemSetting.get_val('default_quota_mb', 51200))
        quota_bytes = default_quota_mb * 1024 * 1024

        new_user = User(
            username=username,
            email=email,
            role='user',
            quota_bytes=quota_bytes,
            used_bytes=0,
            is_active=True
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        AuditService.log_activity(
            action="USER_REGISTER",
            details=f"New user registered: '{username}' with {default_quota_mb} MB quota.",
            user_id=new_user.id
        )

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html', csrf_token=generate_csrf_token())

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    if g.user:
        AuditService.log_activity(
            action="LOGOUT",
            details=f"User '{g.user.username}' logged out.",
            user_id=g.user.id
        )
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if not validate_csrf():
            flash("CSRF validation failed.", "danger")
            return redirect(url_for('auth.profile'))

        action = request.form.get('action')
        if action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not g.user.check_password(current_password):
                flash("Current password is incorrect.", "danger")
                return redirect(url_for('auth.profile'))

            if len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return redirect(url_for('auth.profile'))

            if new_password != confirm_password:
                flash("New passwords do not match.", "danger")
                return redirect(url_for('auth.profile'))

            g.user.set_password(new_password)
            db.session.commit()

            AuditService.log_activity(
                action="PASSWORD_CHANGE",
                details="User successfully changed their password.",
                user_id=g.user.id
            )
            flash("Your password has been updated successfully.", "success")

    return render_template('profile.html', user=g.user, csrf_token=generate_csrf_token())
