import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from models import db
from models.models import Student, BookIssue, Fine, Reservation, Setting
from routes import librarian_or_admin_required
from services.qr_service import generate_student_qr
from services.log_service import log_activity

students_bp = Blueprint('students', __name__, url_prefix='/students')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']

@students_bp.route('/')
@librarian_or_admin_required
def list_students():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    department = request.args.get('dept', '').strip()
    status = request.args.get('status', '').strip()

    query = Student.query
    if search:
        query = query.filter(
            (Student.name.ilike(f"%{search}%")) |
            (Student.student_id.ilike(f"%{search}%")) |
            (Student.email.ilike(f"%{search}%")) |
            (Student.phone.ilike(f"%{search}%"))
        )
    if department:
        query = query.filter_by(department=department)
    if status:
        query = query.filter_by(status=status)

    students_paginated = query.order_by(desc(Student.created_at)).paginate(page=page, per_page=15, error_out=False)
    
    # Get distinct departments for filter dropdown
    departments = [d[0] for d in db.session.query(Student.department).distinct().all() if d[0]]

    return render_template(
        'students/list.html',
        students=students_paginated,
        departments=departments,
        search=search,
        selected_dept=department,
        selected_status=status
    )


@students_bp.route('/add', methods=['GET', 'POST'])
@librarian_or_admin_required
def add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        student_id = request.form.get('student_id', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        department = request.form.get('department', '').strip()
        academic_year = request.form.get('academic_year', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', 'student123').strip()

        if not all([name, student_id, email, department, academic_year, phone]):
            flash('All primary student fields are required.', 'warning')
            return redirect(url_for('students.add'))

        if Student.query.filter_by(student_id=student_id).first():
            flash('A student with this Student ID already exists.', 'danger')
            return redirect(url_for('students.add'))

        if Student.query.filter_by(email=email).first():
            flash('A student with this Email already exists.', 'danger')
            return redirect(url_for('students.add'))

        avatar_filename = 'default_avatar.png'
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '' and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                avatar_filename = f"avatar_{uuid.uuid4().hex[:8]}.{ext}"
                file.save(os.path.join(current_app.config['AVATARS_FOLDER'], avatar_filename))

        new_student = Student(
            student_id=student_id,
            name=name,
            email=email,
            department=department,
            academic_year=academic_year,
            phone=phone,
            address=address,
            avatar=avatar_filename,
            status='active'
        )
        new_student.set_password(password)

        # Generate Student QR
        qr_file = generate_student_qr(student_id, name, department)
        new_student.qr_code_image = qr_file

        db.session.add(new_student)
        db.session.commit()

        log_activity('Add Student', f"Registered student {name} ({student_id})")
        flash(f"Student {name} registered successfully with ID {student_id}!", 'success')
        return redirect(url_for('students.details', student_id=new_student.id))

    return render_template('students/add_edit.html', action='add', student=None)


@students_bp.route('/<int:student_id>')
@librarian_or_admin_required
def details(student_id):
    student = Student.query.get_or_404(student_id)
    active_issues = BookIssue.query.filter_by(student_id=student.id, status='issued').all()
    past_issues = BookIssue.query.filter(BookIssue.student_id == student.id, BookIssue.status != 'issued').order_by(desc(BookIssue.issue_date)).limit(10).all()
    fines = Fine.query.filter_by(student_id=student.id).order_by(desc(Fine.created_at)).all()
    reservations = Reservation.query.filter_by(student_id=student.id).order_by(desc(Reservation.reservation_date)).all()
    currency = Setting.get('currency_symbol', '$')

    return render_template(
        'students/details.html',
        student=student,
        active_issues=active_issues,
        past_issues=past_issues,
        fines=fines,
        reservations=reservations,
        currency=currency
    )


@students_bp.route('/<int:student_id>/edit', methods=['GET', 'POST'])
@librarian_or_admin_required
def edit(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        student.name = request.form.get('name', '').strip()
        student.department = request.form.get('department', '').strip()
        student.academic_year = request.form.get('academic_year', '').strip()
        student.phone = request.form.get('phone', '').strip()
        student.address = request.form.get('address', '').strip()
        student.status = request.form.get('status', 'active')

        new_password = request.form.get('password', '').strip()
        if new_password:
            student.set_password(new_password)

        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '' and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                avatar_filename = f"avatar_{uuid.uuid4().hex[:8]}.{ext}"
                file.save(os.path.join(current_app.config['AVATARS_FOLDER'], avatar_filename))
                student.avatar = avatar_filename

        # Re-generate QR
        qr_file = generate_student_qr(student.student_id, student.name, student.department)
        student.qr_code_image = qr_file

        db.session.commit()
        log_activity('Edit Student', f"Updated info for student {student.name} ({student.student_id})")
        flash(f"Student {student.name} updated successfully.", 'success')
        return redirect(url_for('students.details', student_id=student.id))

    return render_template('students/add_edit.html', action='edit', student=student)


@students_bp.route('/<int:student_id>/delete', methods=['POST'])
@librarian_or_admin_required
def delete(student_id):
    student = Student.query.get_or_404(student_id)
    
    # Check if student has currently issued books
    active = BookIssue.query.filter_by(student_id=student.id, status='issued').count()
    if active > 0:
        flash(f"Cannot delete student {student.name} because they have {active} currently issued book(s).", 'danger')
        return redirect(url_for('students.details', student_id=student.id))

    name = student.name
    code = student.student_id
    db.session.delete(student)
    db.session.commit()

    log_activity('Delete Student', f"Deleted student {name} ({code})")
    flash(f"Student {name} was successfully removed.", 'info')
    return redirect(url_for('students.list_students'))


@students_bp.route('/<int:student_id>/id-card')
def id_card(student_id):
    """
    Renders professional printable student library identity card.
    Accessible by student (for their own card) or librarians/admin.
    """
    student = Student.query.get_or_404(student_id)
    library_name = Setting.get('library_name', 'Apex Central Digital Library')
    contact_email = Setting.get('contact_email', 'library@apex.edu')
    phone = Setting.get('phone_number', '+1 (555) 019-2834')

    return render_template(
        'students/id_card.html',
        student=student,
        library_name=library_name,
        contact_email=contact_email,
        phone=phone
    )


@students_bp.route('/api/search')
def api_search():
    """Live search endpoint for Student ID / Name autocomplete and QR scanner."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    students = Student.query.filter(
        (Student.name.ilike(f"%{q}%")) |
        (Student.student_id.ilike(f"%{q}%")) |
        (Student.email.ilike(f"%{q}%"))
    ).limit(8).all()

    return jsonify([{
        'id': s.id,
        'student_id': s.student_id,
        'name': s.name,
        'department': s.department,
        'academic_year': s.academic_year,
        'active_issues': s.active_issues_count,
        'pending_fines': s.pending_fines_total,
        'status': s.status
    } for s in students])

