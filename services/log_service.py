from flask import request
from flask_login import current_user
from models import db
from models.models import ActivityLog

def log_activity(action, details=None, user_type=None, user_id=None, user_name=None):
    """
    Records an activity audit log into the database.
    Automatically captures current authenticated user and remote IP.
    """
    try:
        if not user_type and current_user.is_authenticated:
            user_type = getattr(current_user, 'role', 'user')
            user_id = getattr(current_user, 'raw_id', None)
            user_name = getattr(current_user, 'name', 'Unknown')
        
        ip_addr = request.remote_addr if request else '127.0.0.1'
        if request and request.headers.get('X-Forwarded-For'):
            ip_addr = request.headers.get('X-Forwarded-For').split(',')[0].strip()

        log_entry = ActivityLog(
            user_type=user_type or 'system',
            user_id=user_id,
            user_name=user_name or 'System',
            action=action,
            details=details or '',
            ip_address=ip_addr
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[Log Error] Failed to write activity log: {e}")

