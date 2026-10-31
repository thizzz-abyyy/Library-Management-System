import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, send_from_directory, request, flash
from flask_login import LoginManager, current_user
from config import Config
from models import db
from models.models import (
    Admin, Librarian, Student, UserSession, Setting, Notification,
    Book, Category, BookIssue, Reservation
)
from init_db import seed_database

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id_composite):
        if not user_id_composite:
            return None
        try:
            parts = user_id_composite.split('_', 1)
            if len(parts) != 2:
                return None
            role, raw_id = parts[0], int(parts[1])

            if role == 'admin':
                admin = Admin.query.get(raw_id)
                return UserSession(admin, 'admin') if admin else None
            elif role == 'librarian':
                lib = Librarian.query.get(raw_id)
                return UserSession(lib, 'librarian') if lib else None
            elif role == 'student':
                stu = Student.query.get(raw_id)
                return UserSession(stu, 'student') if stu else None
        except Exception as e:
            print(f"[Login Manager Error] {e}")
            return None
        return None

    # Global Context Processors for Templates
    @app.context_processor
    def inject_global_data():
        library_name = Setting.get('library_name', 'Apex Central Digital Library')
        currency_symbol = Setting.get('currency_symbol', '$')
        
        unread_notif_count = 0
        admin_pending_issues = 0
        admin_pending_res = 0

        if current_user.is_authenticated:
            if current_user.role == 'student':
                unread_notif_count = Notification.query.filter(
                    ((Notification.recipient_type == 'student') & (Notification.recipient_id == current_user.raw_id)) |
                    (Notification.recipient_type == 'all'),
                    Notification.is_read == False
                ).count()
            elif current_user.role in ('admin', 'librarian'):
                unread_notif_count = Notification.query.filter(
                    (Notification.recipient_type.in_(['admin', 'librarian', 'all'])),
                    Notification.is_read == False
                ).count()
                admin_pending_issues = BookIssue.query.filter(
                    (BookIssue.status == 'overdue') |
                    ((BookIssue.status == 'issued') & (BookIssue.due_date < datetime.utcnow()))
                ).count()
                admin_pending_res = Reservation.query.filter_by(status='pending').count()

        return dict(
            library_name=library_name,
            currency_symbol=currency_symbol,
            unread_notif_count=unread_notif_count,
            admin_pending_issues=admin_pending_issues,
            admin_pending_res=admin_pending_res,
            current_year=datetime.utcnow().year
        )

    # Route for serving uploaded files securely (supports local repo and serverless /tmp)
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        target = Path(app.config['UPLOAD_FOLDER']) / filename
        if target.exists():
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        repo_upload = Path(__file__).resolve().parent / 'uploads' / filename
        if repo_upload.exists():
            return send_from_directory(repo_upload.parent, repo_upload.name)
        # Fallback to default asset if file not found
        if 'cover' in filename.lower() or 'book' in filename.lower():
            return send_from_directory(Path(__file__).resolve().parent / 'static' / 'images', 'default_book_cover.png')
        return send_from_directory(Path(__file__).resolve().parent / 'static' / 'images', 'default_avatar.png')

    # Public Landing Page / Catalog Explorer
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('auth.dashboard_redirect'))
        
        # Display featured catalog & stats on public home
        total_books = db.session.query(db.func.coalesce(db.func.sum(Book.total_copies), 0)).scalar()
        total_titles = Book.query.count()
        total_students = Student.query.count()
        categories = Category.query.all()
        featured_books = Book.query.filter(Book.available_copies > 0).order_by(Book.created_at.desc()).limit(8).all()
        
        return render_template(
            'index.html',
            total_books=int(total_books),
            total_titles=total_titles,
            total_students=total_students,
            categories=categories,
            featured_books=featured_books
        )

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.books import books_bp
    from routes.students import students_bp
    from routes.issues import issues_bp
    from routes.fines import fines_bp
    from routes.reservations import reservations_bp
    from routes.ebooks import ebooks_bp
    from routes.student import student_bp
    from routes.reports import reports_bp
    from routes.locations import locations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(fines_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(ebooks_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(locations_bp)

    @app.route('/find-book')
    def find_book_alias():
        return redirect(url_for('locations.find_book'))

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('components/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('components/500.html'), 500

    # Auto-initialize database tables and seeds within app context
    with app.app_context():
        try:
            db.create_all()
            seed_database()
        except Exception as e:
            print(f"[Init Warning] Database setup note: {e}")

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

