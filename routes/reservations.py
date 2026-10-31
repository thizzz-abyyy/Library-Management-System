from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import desc
from models import db
from models.models import Reservation, Book, Student
from routes import librarian_or_admin_required
from services.log_service import log_activity
from services.notification_service import create_notification

reservations_bp = Blueprint('reservations', __name__, url_prefix='/reservations')

@reservations_bp.route('/')
@librarian_or_admin_required
def list_reservations():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('q', '').strip()

    query = Reservation.query

    if status:
        query = query.filter_by(status=status)

    if search:
        query = query.join(Student).join(Book).filter(
            (Reservation.reservation_code.ilike(f"%{search}%")) |
            (Student.name.ilike(f"%{search}%")) |
            (Student.student_id.ilike(f"%{search}%")) |
            (Book.title.ilike(f"%{search}%"))
        )

    reservations_paginated = query.order_by(Reservation.status.asc(), Reservation.queue_position.asc(), desc(Reservation.reservation_date))\
                                 .paginate(page=page, per_page=15, error_out=False)

    return render_template(
        'reservations/list.html',
        reservations=reservations_paginated,
        status=status,
        search=search
    )


@reservations_bp.route('/<int:res_id>/fulfill', methods=['POST'])
@librarian_or_admin_required
def fulfill_reservation(res_id):
    """Marks reservation as fulfilled and redirects to issue book page."""
    reservation = Reservation.query.get_or_404(res_id)
    reservation.status = 'fulfilled'
    db.session.commit()

    log_activity(
        'Fulfill Reservation',
        f"Fulfilled reservation {reservation.reservation_code} for {reservation.student.name} ({reservation.book.title})"
    )

    flash(f"Reservation for '{reservation.book.title}' fulfilled. Redirecting to issue form...", 'success')
    return redirect(url_for('issues.issue_book', book_id=reservation.book_id, student_id=reservation.student.student_id))


@reservations_bp.route('/<int:res_id>/cancel', methods=['POST'])
@librarian_or_admin_required
def cancel_reservation(res_id):
    reservation = Reservation.query.get_or_404(res_id)
    reason = request.form.get('cancel_reason', 'Cancelled by librarian').strip()

    reservation.status = 'cancelled'
    reservation.notes = (reservation.notes or '') + f" | Cancelled: {reason}"
    db.session.commit()

    create_notification(
        recipient_type='student',
        recipient_id=reservation.student_id,
        title="Reservation Cancelled",
        message=f"Your reservation for '{reservation.book.title}' has been cancelled. Reason: {reason}",
        notif_type='warning',
        link='/student/my-books'
    )

    log_activity(
        'Cancel Reservation',
        f"Cancelled reservation {reservation.reservation_code} for {reservation.student.name}"
    )

    flash(f"Reservation {reservation.reservation_code} has been cancelled.", 'info')
    return redirect(url_for('reservations.list_reservations'))

