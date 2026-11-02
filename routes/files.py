import mimetypes
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, send_file, jsonify, abort
from .auth import login_required, validate_csrf, generate_csrf_token
from models.database import FileItem, db, format_bytes
from services.quota_service import QuotaService, QuotaExceededError
from services.storage_service import get_file_stream
from services.audit_service import AuditService

files_bp = Blueprint('files', __name__)

@files_bp.route('/files')
@login_required
def list_files():
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')

    query = FileItem.query.filter_by(user_id=g.user.id)

    if search_query:
        query = query.filter(FileItem.original_filename.ilike(f'%{search_query}%'))

    # Sorting
    if sort_by == 'name':
        query = query.order_by(FileItem.original_filename.desc() if order == 'desc' else FileItem.original_filename.asc())
    elif sort_by == 'size':
        query = query.order_by(FileItem.size_bytes.desc() if order == 'desc' else FileItem.size_bytes.asc())
    else:  # default 'date'
        query = query.order_by(FileItem.created_at.desc() if order == 'desc' else FileItem.created_at.asc())

    files = query.all()
    total_files_size = sum(f.size_bytes for f in files)

    return render_template(
        'files.html',
        files=files,
        total_files_size=format_bytes(total_files_size),
        search_query=search_query,
        sort_by=sort_by,
        order=order,
        csrf_token=generate_csrf_token()
    )

@files_bp.route('/files/upload', methods=['POST'])
@login_required
def upload_file():
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    if not validate_csrf():
        msg = "Security validation failed (Invalid CSRF token)."
        if is_ajax:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for('files.list_files'))

    if 'file' not in request.files:
        msg = "No file selected in request."
        if is_ajax:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for('files.list_files'))

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        msg = "Please select a valid file to upload."
        if is_ajax:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for('files.list_files'))

    filename = uploaded_file.filename
    mime_type = uploaded_file.mimetype or mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    try:
        # Enforce quota check & transaction upload
        file_record = QuotaService.process_file_upload(
            user_id=g.user.id,
            file_storage=uploaded_file,
            original_filename=filename,
            mime_type=mime_type
        )

        success_msg = f"File '{file_record.original_filename}' ({file_record.readable_size}) successfully uploaded!"
        if is_ajax:
            return jsonify({
                "success": True,
                "message": success_msg,
                "file": file_record.to_dict(),
                "quota": QuotaService.get_user_quota_info(g.user.id)
            })
        flash(success_msg, "success")
        return redirect(url_for('files.list_files'))

    except QuotaExceededError as qe:
        msg = str(qe)
        if is_ajax:
            return jsonify({"success": False, "message": msg, "quota_exceeded": True}), 400
        flash(msg, "danger")
        return redirect(url_for('files.list_files'))

    except ValueError as ve:
        msg = str(ve)
        if is_ajax:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "warning")
        return redirect(url_for('files.list_files'))

    except Exception as e:
        msg = f"Upload failed due to storage error: {str(e)}"
        if is_ajax:
            return jsonify({"success": False, "message": msg}), 500
        flash(msg, "danger")
        return redirect(url_for('files.list_files'))

@files_bp.route('/files/<int:file_id>/download')
@login_required
def download_file(file_id):
    file_record = FileItem.query.get_or_404(file_id)

    # Strict authorization check: users can ONLY download their own files, unless admin
    if file_record.user_id != g.user.id and not g.user.is_admin:
        AuditService.log_activity(
            action="UNAUTHORIZED_DOWNLOAD_ATTEMPT",
            details=f"User {g.user.id} attempted to download file ID {file_id} belonging to user {file_record.user_id}",
            user_id=g.user.id
        )
        abort(403)

    try:
        file_stream_or_path, is_local_path = get_file_stream(file_record.user_id, file_record.stored_filename)

        AuditService.log_activity(
            action="FILE_DOWNLOAD",
            details=f"Downloaded '{file_record.original_filename}' ({file_record.readable_size})",
            user_id=g.user.id
        )

        if is_local_path:
            return send_file(
                file_stream_or_path,
                as_attachment=True,
                download_name=file_record.original_filename,
                mimetype=file_record.mime_type
            )
        else:
            return send_file(
                file_stream_or_path,
                as_attachment=True,
                download_name=file_record.original_filename,
                mimetype=file_record.mime_type
            )

    except FileNotFoundError:
        flash("The requested file was not found in storage.", "danger")
        return redirect(url_for('files.list_files'))
    except Exception as e:
        flash(f"Download failed: {str(e)}", "danger")
        return redirect(url_for('files.list_files'))

@files_bp.route('/files/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file(file_id):
    if not validate_csrf():
        flash("Security validation failed (Invalid CSRF token).", "danger")
        return redirect(url_for('files.list_files'))

    file_record = FileItem.query.get_or_404(file_id)

    # Authorization
    if file_record.user_id != g.user.id and not g.user.is_admin:
        abort(403)

    filename = file_record.original_filename
    try:
        QuotaService.process_file_deletion(
            user_id=g.user.id,
            file_id=file_id,
            is_admin=g.user.is_admin
        )
        flash(f"File '{filename}' has been deleted and storage quota updated.", "info")
    except Exception as e:
        flash(f"Failed to delete file: {str(e)}", "danger")

    return redirect(request.referrer or url_for('files.list_files'))
