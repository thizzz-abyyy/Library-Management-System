from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from models import db
from models.models import Fine, Setting, Student, BookIssue
from routes import librarian_or_admin_required
from services.log_service import log_activity
from services.notification_service import create_notification

fines_bp = Blueprint('fines', __name__, url_prefix='/fines')

@fines_bp.route('/')
@librarian_or_admin_required
def list_fines():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '') # 'pending', 'paid', 'waived'
    search = request.args.get('q', '').strip()

    query = Fine.query

    if status:
        query = query.filter_by(status=status)

    if search:
        query = query.join(Student).join(BookIssue).filter(
            (Student.name.ilike(f"%{search}%")) |
            (Student.student_id.ilike(f"%{search}%")) |
            (Fine.transaction_id.ilike(f"%{search}%"))
        )

    fines_paginated = query.order_by(desc(Fine.created_at)).paginate(page=page, per_page=15, error_out=False)

    total_pending = db.session.query(func.coalesce(func.sum(Fine.amount), 0)).filter_by(status='pending').scalar()
    total_paid = db.session.query(func.coalesce(func.sum(Fine.amount), 0)).filter_by(status='paid').scalar()
    currency = Setting.get('currency_symbol', '$')
    fine_per_day = Setting.get('fine_per_day', '1.00')

    return render_template(
        'fines/list.html',
        fines=fines_paginated,
        status=status,
        search=search,
        total_pending=float(total_pending),
        total_paid=float(total_paid),
        currency=currency,
        fine_per_day=fine_per_day
    )


@fines_bp.route('/<int:fine_id>/pay', methods=['POST'])
@librarian_or_admin_required
def pay_fine(fine_id):
    fine = Fine.query.get_or_404(fine_id)

    if fine.status == 'paid':
        flash('This fine is already marked as paid.', 'info')
        return redirect(url_for('fines.list_fines'))

    payment_method = request.form.get('payment_method', 'Cash')
    transaction_id = request.form.get('transaction_id', '').strip() or f"RCPT-{int(datetime.utcnow().timestamp())}"
    notes = request.form.get('notes', '').strip()

    fine.status = 'paid'
    fine.payment_date = datetime.utcnow()
    fine.payment_method = payment_method
    fine.transaction_id = transaction_id
    if notes:
        fine.notes = (fine.notes or '') + f" | Payment Note: {notes}"

    db.session.commit()

    # Notify student
    create_notification(
        recipient_type='student',
        recipient_id=fine.student_id,
        title="💳 Fine Payment Confirmed",
        message=f"Your fine payment of ${float(fine.amount):.2f} (Receipt: {transaction_id}) has been recorded. Thank you!",
        notif_type='success',
        link='/student/fines'
    )

    log_activity(
        'Fine Payment',
        f"Collected fine ${float(fine.amount):.2f} from {fine.student.name} ({fine.student.student_id}). Method: {payment_method}"
    )

    flash(f"Payment of ${float(fine.amount):.2f} for {fine.student.name} recorded successfully (Receipt #{transaction_id}).", 'success')
    return redirect(url_for('fines.list_fines'))


@fines_bp.route('/<int:fine_id>/waive', methods=['POST'])
@librarian_or_admin_required
def waive_fine(fine_id):
    fine = Fine.query.get_or_404(fine_id)
    reason = request.form.get('waive_reason', 'Administrator discretion').strip()

    fine.status = 'waived'
    fine.payment_date = datetime.utcnow()
    fine.payment_method = 'Waived'
    fine.notes = (fine.notes or '') + f" | Waived Reason: {reason}"

    db.session.commit()

    create_notification(
        recipient_type='student',
        recipient_id=fine.student_id,
        title="✨ Fine Waived",
        message=f"Your fine of ${float(fine.amount):.2f} was waived. Reason: {reason}",
        notif_type='info',
        link='/student/fines'
    )

    log_activity(
        'Fine Waived',
        f"Waived fine of ${float(fine.amount):.2f} for {fine.student.name}. Reason: {reason}"
    )

    flash(f"Fine of ${float(fine.amount):.2f} has been waived.", 'info')
    return redirect(url_for('fines.list_fines'))

