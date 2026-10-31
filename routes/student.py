import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash
from sqlalchemy import desc
from models import db
from models.models import (
    Student, Book, BookIssue, Fine, Reservation, Review, Notification, Setting, Category
)
from routes import student_required
from services.log_service import log_activity
from services.recommendation_service import get_recommendations_for_student
from services.notification_service import create_notification

student_bp = Blueprint('student', __name__, url_prefix='/student')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']


@student_bp.route('/dashboard')
@student_required
def dashboard():
    student = Student.query.get_or_404(current_user.raw_id)
    now = datetime.utcnow()

    # Active Issued Books
    active_issues = BookIssue.query.filter_by(student_id=student.id, status='issued').all()

    # Overdue count
    overdue_count = sum(1 for i in active_issues if i.due_date < now)

    # Active Reservations
    active_reservations = Reservation.query.filter(
        Reservation.student_id == student.id,
        Reservation.status.in_(['pending', 'notified'])
    ).all()

    # Pending Fines
    pending_fines = Fine.query.filter_by(student_id=student.id, status='pending').all()
    pending_fines_total = sum(float(f.amount) for f in pending_fines)

    # Recent Borrowing History
    recent_history = BookIssue.query.filter(
        BookIssue.student_id == student.id,
        BookIssue.status == 'returned'
    ).order_by(desc(BookIssue.return_date)).limit(5).all()

    # AI Recommendations
    recommendations = get_recommendations_for_student(student.id, limit=6)

    # Unread Notifications
    unread_notifs = Notification.query.filter(
        (Notification.recipient_type == 'student') & (Notification.recipient_id == student.id) |
        (Notification.recipient_type == 'all'),
        Notification.is_read == False
    ).order_by(desc(Notification.created_at)).limit(5).all()

    currency = Setting.get('currency_symbol', '$')

    return render_template(
        'student_portal/dashboard.html',
        student=student,
        active_issues=active_issues,
        overdue_count=overdue_count,
        active_reservations=active_reservations,
        pending_fines_total=pending_fines_total,
        recent_history=recent_history,
        recommendations=recommendations,
        unread_notifs=unread_notifs,
        currency=currency
    )


@student_bp.route('/my-books')
@student_required
def my_books():
    student = Student.query.get_or_404(current_user.raw_id)
    active_issues = BookIssue.query.filter_by(student_id=student.id, status='issued').order_by(BookIssue.due_date.asc()).all()
    reservations = Reservation.query.filter_by(student_id=student.id).order_by(desc(Reservation.reservation_date)).all()
    currency = Setting.get('currency_symbol', '$')

    return render_template(
        'student_portal/my_books.html',
        active_issues=active_issues,
        reservations=reservations,
        currency=currency
    )


@student_bp.route('/history')
@student_required
def history():
    page = request.args.get('page', 1, type=int)
    student = Student.query.get_or_404(current_user.raw_id)
    
    history_paginated = BookIssue.query.filter(
        BookIssue.student_id == student.id,
        BookIssue.status == 'returned'
    ).order_by(desc(BookIssue.return_date)).paginate(page=page, per_page=12, error_out=False)

    return render_template('student_portal/history.html', history=history_paginated)


@student_bp.route('/fines')
@student_required
def fines():
    student = Student.query.get_or_404(current_user.raw_id)
    fines_list = Fine.query.filter_by(student_id=student.id).order_by(desc(Fine.created_at)).all()
    currency = Setting.get('currency_symbol', '$')

    total_pending = sum(float(f.amount) for f in fines_list if f.status == 'pending')
    total_paid = sum(float(f.amount) for f in fines_list if f.status == 'paid')

    return render_template(
        'student_portal/fines.html',
        fines=fines_list,
        total_pending=total_pending,
        total_paid=total_paid,
        currency=currency
    )


@student_bp.route('/recommendations')
@student_required
def recommendations():
    student = Student.query.get_or_404(current_user.raw_id)
    recommended = get_recommendations_for_student(student.id, limit=12)
    categories = Category.query.all()

    return render_template(
        'student_portal/recommendations.html',
        books=recommended,
        categories=categories
    )


@student_bp.route('/reserve/<int:book_id>', methods=['POST'])
@student_required
def reserve_book(book_id):
    student = Student.query.get_or_404(current_user.raw_id)
    book = Book.query.get_or_404(book_id)

    # Check if already reserved by this student
    existing = Reservation.query.filter_by(
        student_id=student.id,
        book_id=book.id,
        status='pending'
    ).first()

    if existing:
        flash(f"You already have a pending reservation for '{book.title}' (Queue Position #{existing.queue_position}).", 'warning')
        return redirect(url_for('books.details', book_id=book.id))

    # Determine queue position
    queue_len = Reservation.query.filter_by(book_id=book.id, status='pending').count()
    queue_pos = queue_len + 1

    max_res_id = db.session.query(db.func.max(Reservation.id)).scalar() or 0
    res_code = f"RES-{datetime.utcnow().year}-{(max_res_id + 1):04d}"

    reservation = Reservation(
        reservation_code=res_code,
        book_id=book.id,
        student_id=student.id,
        queue_position=queue_pos,
        status='pending'
    )
    db.session.add(reservation)
    db.session.commit()

    log_activity('Reserve Book', f"Student {student.name} reserved '{book.title}' (Position #{queue_pos})")
    flash(f"Reservation placed successfully for '{book.title}'. You are #{queue_pos} in queue. You will be notified when it becomes available.", 'success')
    return redirect(url_for('student.my_books'))


@student_bp.route('/review/<int:book_id>', methods=['POST'])
@student_required
def submit_review(book_id):
    student = Student.query.get_or_404(current_user.raw_id)
    book = Book.query.get_or_404(book_id)
    rating = request.form.get('rating', 5, type=int)
    review_text = request.form.get('review_text', '').strip()

    # Check if existing review
    existing = Review.query.filter_by(student_id=student.id, book_id=book.id).first()
    if existing:
        existing.rating = rating
        existing.review_text = review_text
        existing.created_at = datetime.utcnow()
        flash('Your review has been updated.', 'success')
    else:
        rev = Review(
            book_id=book.id,
            student_id=student.id,
            rating=max(1, min(5, rating)),
            review_text=review_text
        )
        db.session.add(rev)
        flash('Thank you for rating and reviewing this book!', 'success')

    db.session.commit()
    return redirect(url_for('books.details', book_id=book.id))


@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    student = Student.query.get_or_404(current_user.raw_id)

    if request.method == 'POST':
        student.phone = request.form.get('phone', student.phone).strip()
        student.address = request.form.get('address', student.address).strip()

        old_password = request.form.get('old_password', '').strip()
        new_password = request.form.get('new_password', '').strip()

        if old_password and new_password:
            if not student.check_password(old_password):
                flash('Current password entered is incorrect.', 'danger')
                return redirect(url_for('student.profile'))
            if len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'warning')
                return redirect(url_for('student.profile'))
            student.set_password(new_password)
            flash('Password updated successfully.', 'success')

        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '' and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                avatar_filename = f"avatar_{uuid.uuid4().hex[:8]}.{ext}"
                file.save(os.path.join(current_app.config['AVATARS_FOLDER'], avatar_filename))
                student.avatar = avatar_filename

        db.session.commit()
        log_activity('Profile Update', f"Student {student.name} updated profile.")
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student.profile'))

    return render_template('student_portal/profile.html', student=student)


@student_bp.route('/notifications')
@student_required
def notifications():
    student = Student.query.get_or_404(current_user.raw_id)
    notifs = Notification.query.filter(
        ((Notification.recipient_type == 'student') & (Notification.recipient_id == student.id)) |
        (Notification.recipient_type == 'all')
    ).order_by(desc(Notification.created_at)).all()

    return render_template('student_portal/notifications.html', notifications=notifs)


@student_bp.route('/notifications/mark-read/<int:notif_id>', methods=['POST'])
@student_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@student_bp.route('/notifications/mark-all-read', methods=['POST'])
@student_required
def mark_all_read():
    student_id = current_user.raw_id
    Notification.query.filter(
        ((Notification.recipient_type == 'student') & (Notification.recipient_id == student_id)) |
        (Notification.recipient_type == 'all'),
        Notification.is_read == False
    ).update({'is_read': True}, synchronize_session=False)
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('student.notifications'))

