import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, Response, stream_with_context
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from models import db
from models.models import Book, Student, BookIssue, BookReturn, Fine, Category, ActivityLog, Setting
from routes import librarian_or_admin_required
from services.log_service import log_activity

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@librarian_or_admin_required
def index():
    report_type = request.args.get('type', 'books')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    export = request.args.get('export', '')

    # Parse date filters if provided
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            pass

    records = []
    headers = []
    report_title = "Library Report"

    if report_type == 'books':
        report_title = "Total Books & Catalog Inventory Report"
        headers = ['Book ID', 'ISBN', 'Title', 'Author', 'Category', 'Total Copies', 'Available Copies', 'Shelf Location']
        query = Book.query
        if start_date:
            query = query.filter(Book.created_at >= start_date)
        if end_date:
            query = query.filter(Book.created_at <= end_date)
        books = query.order_by(Book.title.asc()).all()
        for b in books:
            records.append([
                b.id, b.isbn, b.title, b.author,
                b.category_rel.name if b.category_rel else 'Uncategorized',
                b.total_copies, b.available_copies, b.shelf_location or 'N/A'
            ])

    elif report_type == 'students':
        report_title = "Registered Students Report"
        headers = ['Student ID', 'Full Name', 'Department', 'Academic Year', 'Email', 'Phone', 'Status', 'Registration Date']
        query = Student.query
        if start_date:
            query = query.filter(Student.created_at >= start_date)
        if end_date:
            query = query.filter(Student.created_at <= end_date)
        students = query.order_by(Student.name.asc()).all()
        for s in students:
            records.append([
                s.student_id, s.name, s.department, s.academic_year,
                s.email, s.phone, s.status.upper(), s.created_at.strftime('%Y-%m-%d')
            ])

    elif report_type == 'issues':
        report_title = "Book Issue Transactions Report"
        headers = ['Issue Code', 'Book Title', 'Student ID', 'Student Name', 'Issue Date', 'Due Date', 'Status']
        query = BookIssue.query
        if start_date:
            query = query.filter(BookIssue.issue_date >= start_date)
        if end_date:
            query = query.filter(BookIssue.issue_date <= end_date)
        issues = query.order_by(desc(BookIssue.issue_date)).all()
        for i in issues:
            records.append([
                i.issue_code, i.book.title, i.student.student_id, i.student.name,
                i.issue_date.strftime('%Y-%m-%d'), i.due_date.strftime('%Y-%m-%d'), i.status.upper()
            ])

    elif report_type == 'returns':
        report_title = "Book Return Transactions Report"
        headers = ['Return ID', 'Issue Code', 'Book Title', 'Student Name', 'Return Date', 'Overdue Days', 'Fine Amount']
        query = BookReturn.query
        if start_date:
            query = query.filter(BookReturn.return_date >= start_date)
        if end_date:
            query = query.filter(BookReturn.return_date <= end_date)
        returns = query.order_by(desc(BookReturn.return_date)).all()
        for r in returns:
            records.append([
                r.id, r.issue.issue_code if r.issue else 'N/A', r.book.title,
                r.student.name, r.return_date.strftime('%Y-%m-%d'),
                r.overdue_days, f"${float(r.fine_amount):.2f}"
            ])

    elif report_type == 'overdue':
        report_title = "Overdue Books & Delinquency Report"
        headers = ['Issue Code', 'Book Title', 'Student Name', 'Student ID', 'Phone', 'Due Date', 'Overdue Days', 'Accumulated Fine']
        now = datetime.utcnow()
        fine_rate = float(Setting.get('fine_per_day', '1.00'))
        query = BookIssue.query.filter(
            (BookIssue.status == 'overdue') | 
            ((BookIssue.status == 'issued') & (BookIssue.due_date < now))
        )
        if start_date:
            query = query.filter(BookIssue.due_date >= start_date)
        if end_date:
            query = query.filter(BookIssue.due_date <= end_date)
        overdues = query.order_by(BookIssue.due_date.asc()).all()
        for o in overdues:
            days = max(0, (now.date() - o.due_date.date()).days)
            records.append([
                o.issue_code, o.book.title, o.student.name, o.student.student_id,
                o.student.phone, o.due_date.strftime('%Y-%m-%d'), days,
                f"${days * fine_rate:.2f}"
            ])

    elif report_type == 'fines':
        report_title = "Fine Collections and Outstanding Dues Report"
        headers = ['Fine ID', 'Student ID', 'Student Name', 'Amount', 'Status', 'Payment Method', 'Transaction ID', 'Date']
        query = Fine.query
        if start_date:
            query = query.filter(Fine.created_at >= start_date)
        if end_date:
            query = query.filter(Fine.created_at <= end_date)
        fines = query.order_by(desc(Fine.created_at)).all()
        for f in fines:
            records.append([
                f.id, f.student.student_id, f.student.name, f"${float(f.amount):.2f}",
                f.status.upper(), f.payment_method or 'N/A', f.transaction_id or 'N/A',
                f.created_at.strftime('%Y-%m-%d')
            ])

    elif report_type == 'popular':
        report_title = "Most Popular & High Demand Books Report"
        headers = ['Rank', 'Book Title', 'Author', 'Category', 'Total Borrow Count', 'Current Availability']
        popular = db.session.query(
            Book, func.count(BookIssue.id).label('issue_count')
        ).outerjoin(BookIssue, BookIssue.book_id == Book.id)\
         .group_by(Book.id)\
         .order_by(desc('issue_count')).limit(25).all()
        rank = 1
        for b, count in popular:
            records.append([
                rank, b.title, b.author,
                b.category_rel.name if b.category_rel else 'Uncategorized',
                count, f"{b.available_copies} / {b.total_copies}"
            ])
            rank += 1

    # CSV Export Handling
    if export == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(records)
        
        log_activity('Export Report', f"Exported {report_type} report to CSV")
        
        filename = f"{report_type}_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    library_name = Setting.get('library_name', 'Apex Central Digital Library')

    return render_template(
        'reports/index.html',
        report_type=report_type,
        report_title=report_title,
        headers=headers,
        records=records,
        start_date=start_date_str,
        end_date=end_date_str,
        library_name=library_name,
        generated_at=datetime.utcnow().strftime('%B %d, %Y %I:%M %p UTC')
    )

