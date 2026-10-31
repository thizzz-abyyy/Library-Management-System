from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from models import db
from models.models import Book, Student, BookIssue, BookReturn, Fine, Setting, BookLocation
from routes import librarian_or_admin_required
from services.log_service import log_activity
from services.notification_service import create_notification, process_reservation_queue_on_return

issues_bp = Blueprint('issues', __name__, url_prefix='/issues')

@issues_bp.route('/')
@librarian_or_admin_required
def list_issues():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '') # 'issued', 'returned', 'overdue'
    search = request.args.get('q', '').strip()

    query = BookIssue.query

    if status == 'overdue':
        now = datetime.utcnow()
        query = query.filter(
            (BookIssue.status == 'overdue') | 
            ((BookIssue.status == 'issued') & (BookIssue.due_date < now))
        )
    elif status:
        query = query.filter_by(status=status)

    if search:
        query = query.join(Student).join(Book).filter(
            (BookIssue.issue_code.ilike(f"%{search}%")) |
            (Student.name.ilike(f"%{search}%")) |
            (Student.student_id.ilike(f"%{search}%")) |
            (Book.title.ilike(f"%{search}%")) |
            (Book.isbn.ilike(f"%{search}%"))
        )

    issues_paginated = query.order_by(desc(BookIssue.issue_date)).paginate(page=page, per_page=15, error_out=False)
    currency = Setting.get('currency_symbol', '$')

    return render_template(
        'issues/list.html',
        issues=issues_paginated,
        status=status,
        search=search,
        currency=currency
    )


@issues_bp.route('/issue', methods=['GET', 'POST'])
@librarian_or_admin_required
def issue_book():
    if request.method == 'POST':
        student_id_val = request.form.get('student_id', '').strip()
        book_id_val = request.form.get('book_id', '').strip()
        duration_days = request.form.get('duration_days', type=int) or int(Setting.get('issue_duration_days', '14'))
        notes = request.form.get('notes', '').strip()

        # Validate Student
        student = None
        if student_id_val.isdigit():
            student = Student.query.get(int(student_id_val))
        if not student:
            student = Student.query.filter_by(student_id=student_id_val.upper()).first()

        if not student:
            flash(f"Student not found with ID: '{student_id_val}'.", 'danger')
            return redirect(url_for('issues.issue_book'))

        if student.status != 'active':
            flash(f"Student account is suspended ({student.name}). Cannot issue books.", 'danger')
            return redirect(url_for('issues.issue_book'))

        # Check maximum book limit per student
        max_limit = int(Setting.get('max_books_per_student', '3'))
        current_borrowed = student.active_issues_count
        if current_borrowed >= max_limit:
            flash(f"Student has already reached the maximum allowed limit of {max_limit} borrowed books.", 'danger')
            return redirect(url_for('issues.issue_book'))

        # Validate Book
        book = None
        if book_id_val.isdigit():
            book = Book.query.get(int(book_id_val))
        if not book:
            book = Book.query.filter_by(isbn=book_id_val).first()

        if not book:
            flash(f"Book not found with ID or ISBN: '{book_id_val}'.", 'danger')
            return redirect(url_for('issues.issue_book'))

        # Check availability
        if book.available_copies <= 0:
            flash(f"Book '{book.title}' is currently out of stock (0 available copies).", 'danger')
            return redirect(url_for('issues.issue_book'))

        # Check if student already has a copy of this book currently issued
        existing = BookIssue.query.filter_by(student_id=student.id, book_id=book.id, status='issued').first()
        if existing:
            flash(f"Student {student.name} already has a copy of '{book.title}' currently issued.", 'warning')
            return redirect(url_for('issues.issue_book'))

        # Generate Issue Code
        max_iss_id = db.session.query(db.func.max(BookIssue.id)).scalar() or 0
        issue_code = f"ISS-{datetime.utcnow().year}-{(max_iss_id + 1):04d}"

        # Calculate Dates
        issue_date = datetime.utcnow()
        due_date = issue_date + timedelta(days=duration_days)

        # Create Issue Record
        new_issue = BookIssue(
            issue_code=issue_code,
            book_id=book.id,
            student_id=student.id,
            issued_by_type=getattr(current_user, 'role', 'admin'),
            issued_by_id=getattr(current_user, 'raw_id', 1),
            issue_date=issue_date,
            due_date=due_date,
            status='issued',
            notes=notes
        )

        # Decrement Available Copies
        book.available_copies = max(0, book.available_copies - 1)

        # Track physical copy location status
        avail_copy = BookLocation.query.filter_by(book_id=book.id, status='on_shelf').first()
        if avail_copy:
            avail_copy.status = 'issued'
            avail_copy.notes = f"Issued under loan {issue_code} to {student.name}"

        db.session.add(new_issue)
        db.session.commit()

        # Notification for student
        create_notification(
            recipient_type='student',
            recipient_id=student.id,
            title="📖 Book Issued Successfully",
            message=f"You borrowed '{book.title}'. Due date is {due_date.strftime('%Y-%m-%d')}.",
            notif_type='success',
            link='/student/my-books'
        )

        log_activity(
            'Issue Book',
            f"Issued '{book.title}' to {student.name} ({student.student_id}). Issue Code: {issue_code}"
        )

        flash(f"Book '{book.title}' successfully issued to {student.name}! Due Date: {due_date.strftime('%b %d, %Y')}.", 'success')
        return redirect(url_for('issues.list_issues'))

    default_days = int(Setting.get('issue_duration_days', '14'))
    prefill_book = request.args.get('book_id')
    prefill_student = request.args.get('student_id')
    
    return render_template(
        'issues/issue_book.html',
        default_days=default_days,
        prefill_book=prefill_book,
        prefill_student=prefill_student
    )


@issues_bp.route('/return', methods=['GET', 'POST'])
@librarian_or_admin_required
def return_book():
    if request.method == 'POST':
        issue_id = request.form.get('issue_id', type=int)
        condition_notes = request.form.get('condition_notes', '').strip()
        fine_action = request.form.get('fine_action', 'pending') # 'pending', 'paid', 'waive'
        payment_method = request.form.get('payment_method', 'Cash')

        issue = BookIssue.query.get_or_404(issue_id)
        if issue.status == 'returned':
            flash('This book issue has already been returned.', 'warning')
            return redirect(url_for('issues.list_issues'))

        now = datetime.utcnow()
        overdue_days = max(0, (now.date() - issue.due_date.date()).days)
        fine_rate = float(Setting.get('fine_per_day', '1.00'))
        calculated_fine = overdue_days * fine_rate

        # Update Issue Record
        issue.return_date = now
        issue.status = 'returned'

        # Increment Book Available Count
        issue.book.available_copies = min(issue.book.total_copies, issue.book.available_copies + 1)

        # Update physical shelf location confirmation
        confirm_shelf = bool(request.form.get('confirm_shelf_placement'))
        issued_copy = BookLocation.query.filter_by(book_id=issue.book_id, status='issued').first()
        if issued_copy and confirm_shelf:
            issued_copy.status = 'on_shelf'
            issued_copy.last_confirmed_at = now
            issued_copy.notes = f"Returned and re-shelved by staff at {now.strftime('%Y-%m-%d %H:%M')}"
        elif issued_copy and not confirm_shelf:
            issued_copy.notes = f"Returned to counter; pending physical shelf placement"

        # Create Book Return Record
        return_rec = BookReturn(
            issue_id=issue.id,
            book_id=issue.book_id,
            student_id=issue.student_id,
            received_by_type=getattr(current_user, 'role', 'admin'),
            received_by_id=getattr(current_user, 'raw_id', 1),
            return_date=now,
            overdue_days=overdue_days,
            fine_amount=calculated_fine,
            condition_notes=condition_notes
        )
        db.session.add(return_rec)

        # Handle Fine if applicable
        if calculated_fine > 0:
            fine_status = 'pending'
            payment_date = None
            if fine_action == 'paid':
                fine_status = 'paid'
                payment_date = now
            elif fine_action == 'waive':
                fine_status = 'waived'
                payment_date = now

            fine_record = Fine(
                issue_id=issue.id,
                student_id=issue.student_id,
                amount=calculated_fine,
                overdue_days=overdue_days,
                status=fine_status,
                payment_date=payment_date,
                payment_method=payment_method if fine_status == 'paid' else None,
                transaction_id=f"TXN-{int(now.timestamp())}" if fine_status == 'paid' else None,
                notes=f"Return fine: {overdue_days} overdue days @ {fine_rate}/day"
            )
            db.session.add(fine_record)

        db.session.commit()

        # Check reservation queue for this book
        process_reservation_queue_on_return(issue.book_id)

        # Notification for student
        create_notification(
            recipient_type='student',
            recipient_id=issue.student_id,
            title="📚 Book Returned Successfully",
            message=f"You returned '{issue.book.title}'. Thank you!",
            notif_type='info',
            link='/student/my-books'
        )

        log_activity(
            'Return Book',
            f"Returned '{issue.book.title}' from {issue.student.name}. Overdue: {overdue_days} days. Fine: {calculated_fine}"
        )

        flash(f"Book '{issue.book.title}' returned successfully. {f'Late fee of ${calculated_fine:.2f} recorded ({fine_action}).' if calculated_fine > 0 else 'No late fees.'}", 'success')
        return redirect(url_for('issues.list_issues'))

    # If GET with issue_id parameter, load return confirmation view
    issue_id = request.args.get('issue_id', type=int)
    issue = BookIssue.query.get(issue_id) if issue_id else None
    
    currency = Setting.get('currency_symbol', '$')
    fine_rate = float(Setting.get('fine_per_day', '1.00'))

    return render_template(
        'issues/return_book.html',
        issue=issue,
        currency=currency,
        fine_rate=fine_rate
    )


@issues_bp.route('/api/lookup')
def api_lookup():
    """Lookup issue by QR scan or issue code/student ID."""
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'found': False, 'message': 'No code provided'})

    # Try issue_code match
    issue = BookIssue.query.filter_by(issue_code=code, status='issued').first()
    
    # Try book ID or ISBN if it's currently issued
    if not issue and code.isdigit():
        issue = BookIssue.query.filter_by(book_id=int(code), status='issued').order_by(BookIssue.issue_date.asc()).first()

    if not issue:
        # Check student ID
        student = Student.query.filter((Student.student_id == code.upper()) | (Student.id == (int(code) if code.isdigit() else -1))).first()
        if student:
            active = BookIssue.query.filter_by(student_id=student.id, status='issued').all()
            return jsonify({
                'found': True,
                'type': 'student',
                'student': {
                    'id': student.id,
                    'name': student.name,
                    'student_id': student.student_id,
                    'active_issues': [{'id': i.id, 'issue_code': i.issue_code, 'book_title': i.book.title} for i in active]
                }
            })
        return jsonify({'found': False, 'message': 'No active issue found matching query.'})

    now = datetime.utcnow()
    overdue_days = max(0, (now.date() - issue.due_date.date()).days)
    fine_rate = float(Setting.get('fine_per_day', '1.00'))

    return jsonify({
        'found': True,
        'type': 'issue',
        'issue': {
            'id': issue.id,
            'issue_code': issue.issue_code,
            'book_title': issue.book.title,
            'book_isbn': issue.book.isbn,
            'student_name': issue.student.name,
            'student_id': issue.student.student_id,
            'issue_date': issue.issue_date.strftime('%Y-%m-%d'),
            'due_date': issue.due_date.strftime('%Y-%m-%d'),
            'overdue_days': overdue_days,
            'calculated_fine': overdue_days * fine_rate,
            'location_display': issue.book.primary_location_display
        }
    })

