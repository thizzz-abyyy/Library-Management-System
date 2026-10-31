from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            user_role = getattr(current_user, 'role', None)
            if user_role not in allowed_roles:
                flash('Access denied. You do not have permission for this section.', 'danger')
                return redirect(url_for('auth.dashboard_redirect'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return role_required('admin')(f)

def librarian_or_admin_required(f):
    return role_required('admin', 'librarian')(f)

def student_required(f):
    return role_required('student')(f)

