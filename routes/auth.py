from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import db
from models.models import Admin, Librarian, Student, UserSession, Setting
from services.log_service import log_activity
from services.qr_service import generate_student_qr

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard_redirect'))
        
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '').strip()
        role_type = request.form.get('role_type', 'auto') # 'auto', 'admin', 'librarian', 'student'
        remember = bool(request.form.get('remember'))

        if not login_id or not password:
            flash('Please provide both username/ID/email and password.', 'warning')
            return render_template('auth/login.html')

        user_found = None
        role_found = None

        # Check Admin
        if role_type in ('auto', 'admin'):
            admin = Admin.query.filter((Admin.username == login_id) | (Admin.email == login_id)).first()
            if admin and admin.check_password(password):
                user_found = admin
                role_found = 'admin'

        # Check Librarian
        if not user_found and role_type in ('auto', 'librarian'):
            librarian = Librarian.query.filter(
                (Librarian.librarian_id == login_id) | (Librarian.email == login_id)
            ).first()
            if librarian and librarian.check_password(password):
                if librarian.status != 'active':
                    flash('Your librarian account is currently deactivated. Please contact the administrator.', 'danger')
                    return render_template('auth/login.html')
                user_found = librarian
                role_found = 'librarian'

        # Check Student
        if not user_found and role_type in ('auto', 'student'):
            student = Student.query.filter(
                (Student.student_id == login_id) | (Student.email == login_id)
            ).first()
            if student and student.check_password(password):
                if student.status != 'active':
                    flash('Your student account is suspended. Please visit the library administration.', 'danger')
                    return render_template('auth/login.html')
                user_found = student
                role_found = 'student'

        if user_found:
            session_user = UserSession(user_found, role_found)
            login_user(session_user, remember=remember)
            log_activity(
                action='User Login',
                details=f"Successful login as {role_found.upper()}",
                user_type=role_found,
                user_id=user_found.id,
                user_name=user_found.name
            )
            flash(f"Welcome back, {user_found.name}!", 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('auth.dashboard_redirect'))
        else:
            flash('Invalid credentials. Please verify your ID/Email and password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard_redirect'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        student_id = request.form.get('student_id', '').strip().upper()
        department = request.form.get('department', '').strip()
        academic_year = request.form.get('academic_year', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not all([name, email, student_id, department, academic_year, phone, password]):
            flash('All required fields must be filled.', 'warning')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('auth/register.html')

        # Check existing email or student_id
        if Student.query.filter_by(email=email).first():
            flash('A student account with this email address already exists.', 'danger')
            return render_template('auth/register.html')

        if Student.query.filter_by(student_id=student_id).first():
            flash('A student account with this Student ID already exists.', 'danger')
            return render_template('auth/register.html')

        new_student = Student(
            student_id=student_id,
            name=name,
            email=email,
            department=department,
            academic_year=academic_year,
            phone=phone,
            address=address,
            status='active'
        )
        new_student.set_password(password)

        # Generate Student QR Code
        qr_file = generate_student_qr(student_id, name, department)
        new_student.qr_code_image = qr_file

        db.session.add(new_student)
        db.session.commit()

        log_activity(
            action='Student Registration',
            details=f"New student registration: {name} ({student_id})",
            user_type='student',
            user_id=new_student.id,
            user_name=name
        )

        flash('Registration successful! You can now log in to the Student Portal.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/dashboard')
@login_required
def dashboard_redirect():
    role = getattr(current_user, 'role', None)
    if role in ('admin', 'librarian'):
        return redirect(url_for('admin.dashboard'))
    elif role == 'student':
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    log_activity(
        action='User Logout',
        details=f"User {current_user.name} logged out."
    )
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))

