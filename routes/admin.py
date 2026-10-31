from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from models import db
from models.models import (
    Admin, Librarian, Student, Book, BookIssue, BookReturn,
    Reservation, Fine, Category, ActivityLog, Setting, Notification,
    Floor, Section, Room, Rack, Shelf, BookLocation
)
from routes import admin_required, librarian_or_admin_required
from services.log_service import log_activity
from services.notification_service import notify_overdue_books
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@librarian_or_admin_required
def dashboard():
    # Scan and update overdue books automatically
    notify_overdue_books()

    now = datetime.utcnow()
    
    # 1. High-Level KPI Statistics
    total_titles = Book.query.count()
    total_books = db.session.query(func.coalesce(func.sum(Book.total_copies), 0)).scalar()
    available_books = db.session.query(func.coalesce(func.sum(Book.available_copies), 0)).scalar()
    total_students = Student.query.count()
    total_librarians = Librarian.query.count()
    
    active_issues = BookIssue.query.filter_by(status='issued').count()
    overdue_issues = BookIssue.query.filter(
        (BookIssue.status == 'overdue') | 
        ((BookIssue.status == 'issued') & (BookIssue.due_date < now))
    ).count()
    
    pending_reservations = Reservation.query.filter_by(status='pending').count()
    
    total_fines_collected = db.session.query(
        func.coalesce(func.sum(Fine.amount), 0.0)
    ).filter_by(status='paid').scalar()
    
    total_fines_pending = db.session.query(
        func.coalesce(func.sum(Fine.amount), 0.0)
    ).filter_by(status='pending').scalar()

    # 2. Recent Book Issues & Returns
    recent_issues = BookIssue.query.order_by(desc(BookIssue.issue_date)).limit(5).all()
    recent_returns = BookReturn.query.order_by(desc(BookReturn.return_date)).limit(5).all()

    # 3. Popular Books (most issued)
    popular_books = db.session.query(
        Book, func.count(BookIssue.id).label('issue_count')
    ).outerjoin(BookIssue, BookIssue.book_id == Book.id)\
     .group_by(Book.id)\
     .order_by(desc('issue_count')).limit(5).all()

    # 4. Recently Added Books
    recently_added = Book.query.order_by(desc(Book.created_at)).limit(5).all()

    # 5. Urgent Overdue Alerts
    overdue_list = BookIssue.query.filter(
        (BookIssue.status == 'overdue') | 
        ((BookIssue.status == 'issued') & (BookIssue.due_date < now))
    ).order_by(BookIssue.due_date.asc()).limit(5).all()

    # 6. Monthly Issue Statistics for Chart.js (Last 6 Months)
    monthly_labels = []
    monthly_issue_data = []
    monthly_return_data = []

    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i * 30)
        month_name = target_date.strftime('%b %Y')
        month_start = datetime(target_date.year, target_date.month, 1)
        if target_date.month == 12:
            month_end = datetime(target_date.year + 1, 1, 1)
        else:
            month_end = datetime(target_date.year, target_date.month + 1, 1)
        
        issue_cnt = BookIssue.query.filter(
            BookIssue.issue_date >= month_start,
            BookIssue.issue_date < month_end
        ).count()
        
        return_cnt = BookReturn.query.filter(
            BookReturn.return_date >= month_start,
            BookReturn.return_date < month_end
        ).count()
        
        monthly_labels.append(month_name)
        monthly_issue_data.append(issue_cnt)
        monthly_return_data.append(return_cnt)

    # 7. Category Distribution for Chart.js
    category_stats = db.session.query(
        Category.name, func.coalesce(func.sum(Book.total_copies), 0)
    ).join(Book, Book.category_id == Category.id, isouter=True)\
     .group_by(Category.id)\
     .order_by(desc(func.coalesce(func.sum(Book.total_copies), 0))).limit(6).all()
     
    cat_labels = [c[0] for c in category_stats]
    cat_counts = [int(c[1]) for c in category_stats]

    # 8. Smart Book Shelf & Location Tracking Metrics
    total_floors = Floor.query.count()
    total_sections = Section.query.count()
    total_racks = Rack.query.count()
    total_shelves = Shelf.query.count()
    total_located_books = BookLocation.query.filter(BookLocation.shelf_id.isnot(None)).count()
    unassigned_books = Book.query.filter(~Book.id.in_(db.session.query(BookLocation.book_id))).count()

    # Get currency symbol setting
    currency = Setting.get('currency_symbol', '$')

    return render_template(
        'admin/dashboard.html',
        total_titles=total_titles,
        total_books=int(total_books),
        available_books=int(available_books),
        total_students=total_students,
        total_librarians=total_librarians,
        active_issues=active_issues,
        overdue_issues=overdue_issues,
        pending_reservations=pending_reservations,
        total_fines_collected=float(total_fines_collected),
        total_fines_pending=float(total_fines_pending),
        recent_issues=recent_issues,
        recent_returns=recent_returns,
        popular_books=popular_books,
        recently_added=recently_added,
        overdue_list=overdue_list,
        monthly_labels=monthly_labels,
        monthly_issue_data=monthly_issue_data,
        monthly_return_data=monthly_return_data,
        cat_labels=cat_labels,
        cat_counts=cat_counts,
        currency=currency,
        total_floors=total_floors,
        total_sections=total_sections,
        total_racks=total_racks,
        total_shelves=total_shelves,
        total_located_books=total_located_books,
        unassigned_books=unassigned_books
    )


# ==========================================
# LIBRARIAN MANAGEMENT
# ==========================================

@admin_bp.route('/librarians', methods=['GET', 'POST'])
@admin_required
def librarians():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '').strip()
            permissions = request.form.getlist('permissions')

            if not all([name, email, password]):
                flash('Name, email, and password are required.', 'warning')
                return redirect(url_for('admin.librarians'))

            if Librarian.query.filter_by(email=email).first():
                flash('A librarian with this email already exists.', 'danger')
                return redirect(url_for('admin.librarians'))

            # Auto-generate Librarian ID
            count = Librarian.query.count() + 1
            lib_id = f"LIB-{count:03d}"

            librarian = Librarian(
                librarian_id=lib_id,
                name=name,
                email=email,
                phone=phone,
                permissions=",".join(permissions) if permissions else "books,issues,returns,reservations",
                status='active'
            )
            librarian.set_password(password)
            db.session.add(librarian)
            db.session.commit()

            log_activity('Add Librarian', f"Created librarian {name} ({lib_id})")
            flash(f"Librarian {name} created successfully with ID {lib_id}.", 'success')
            return redirect(url_for('admin.librarians'))

        elif action == 'edit':
            lib_id = request.form.get('id')
            librarian = Librarian.query.get_or_404(lib_id)

            librarian.name = request.form.get('name', '').strip()
            librarian.phone = request.form.get('phone', '').strip()
            librarian.status = request.form.get('status', 'active')
            
            perms = request.form.getlist('permissions')
            librarian.permissions = ",".join(perms) if perms else "books,issues,returns"

            new_pw = request.form.get('password', '').strip()
            if new_pw:
                librarian.set_password(new_pw)

            db.session.commit()
            log_activity('Edit Librarian', f"Updated librarian {librarian.name} ({librarian.librarian_id})")
            flash(f"Librarian {librarian.name} updated successfully.", 'success')
            return redirect(url_for('admin.librarians'))

        elif action == 'delete':
            lib_id = request.form.get('id')
            librarian = Librarian.query.get_or_404(lib_id)
            name = librarian.name
            lib_code = librarian.librarian_id

            db.session.delete(librarian)
            db.session.commit()
            log_activity('Delete Librarian', f"Deleted librarian {name} ({lib_code})")
            flash(f"Librarian {name} removed successfully.", 'info')
            return redirect(url_for('admin.librarians'))

    librarians_list = Librarian.query.order_by(Librarian.id.desc()).all()
    return render_template('admin/librarians.html', librarians=librarians_list)


# ==========================================
# ACTIVITY LOGS & AUDIT TRAIL
# ==========================================

@admin_bp.route('/activity-logs')
@admin_required
def activity_logs():
    page = request.args.get('page', 1, type=int)
    user_type = request.args.get('user_type', '')
    search = request.args.get('q', '').strip()

    query = ActivityLog.query
    if user_type:
        query = query.filter_by(user_type=user_type)
    if search:
        query = query.filter(
            (ActivityLog.action.ilike(f"%{search}%")) |
            (ActivityLog.details.ilike(f"%{search}%")) |
            (ActivityLog.user_name.ilike(f"%{search}%"))
        )

    logs_paginated = query.order_by(desc(ActivityLog.created_at)).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/activity_logs.html', logs=logs_paginated, user_type=user_type, search=search)


# ==========================================
# SETTINGS MODULE
# ==========================================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        settings_dict = {
            'library_name': request.form.get('library_name', 'Apex Central Library'),
            'contact_email': request.form.get('contact_email', 'library@apex.edu'),
            'phone_number': request.form.get('phone_number', '+1 (555) 019-2834'),
            'address': request.form.get('address', '100 University Avenue, Tech Campus, Building B'),
            'currency_symbol': request.form.get('currency_symbol', '$'),
            'fine_per_day': request.form.get('fine_per_day', '1.00'),
            'issue_duration_days': request.form.get('issue_duration_days', '14'),
            'max_books_per_student': request.form.get('max_books_per_student', '3'),
            'reservation_hold_hours': request.form.get('reservation_hold_hours', '48')
        }

        for k, v in settings_dict.items():
            Setting.set(k, v)

        log_activity('Update Settings', "Updated library system configuration.")
        flash('Library settings saved successfully.', 'success')
        return redirect(url_for('admin.settings'))

    current_settings = {
        'library_name': Setting.get('library_name', 'Apex Central Digital Library'),
        'contact_email': Setting.get('contact_email', 'library@apex.edu'),
        'phone_number': Setting.get('phone_number', '+1 (555) 019-2834'),
        'address': Setting.get('address', '100 University Avenue, Tech Campus, Building B'),
        'currency_symbol': Setting.get('currency_symbol', '$'),
        'fine_per_day': Setting.get('fine_per_day', '1.00'),
        'issue_duration_days': Setting.get('issue_duration_days', '14'),
        'max_books_per_student': Setting.get('max_books_per_student', '3'),
        'reservation_hold_hours': Setting.get('reservation_hold_hours', '48')
    }

    return render_template('admin/settings.html', settings=current_settings)


# ==========================================
# DATABASE BACKUP HELPER
# ==========================================

@admin_bp.route('/backup')
@admin_required
def backup_database():
    data = {
        'exported_at': datetime.utcnow().isoformat(),
        'system': Setting.get('library_name', 'Apex Digital Library'),
        'categories': [{'id': c.id, 'name': c.name, 'description': c.description} for c in Category.query.all()],
        'books': [{
            'id': b.id, 'isbn': b.isbn, 'title': b.title, 'author': b.author,
            'publisher': b.publisher, 'category_id': b.category_id,
            'total_copies': b.total_copies, 'available_copies': b.available_copies
        } for b in Book.query.all()],
        'students': [{
            'student_id': s.student_id, 'name': s.name, 'email': s.email,
            'department': s.department, 'status': s.status
        } for s in Student.query.all()]
    }
    
    json_str = json.dumps(data, indent=2)
    filename = f"library_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    log_activity('Database Backup', f"Generated database snapshot {filename}")
    return Response(
        json_str,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )

