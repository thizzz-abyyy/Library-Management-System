from datetime import datetime, timedelta
from models import db
from models.models import Notification, BookIssue, Reservation, Book, Student, Setting

def create_notification(recipient_type, recipient_id, title, message, notif_type='info', link=None):
    """
    Creates an in-app notification.
    recipient_type: 'student', 'librarian', 'admin', 'all'
    """
    try:
        notif = Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            title=title,
            message=message,
            type=notif_type,
            link=link
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        db.session.rollback()
        print(f"[Notification Error] {e}")
        return None

def notify_overdue_books():
    """
    Scans for overdue books and generates alerts for students and librarians/admins.
    """
    now = datetime.utcnow()
    overdue_issues = BookIssue.query.filter(
        BookIssue.status == 'issued',
        BookIssue.due_date < now
    ).all()

    for issue in overdue_issues:
        issue.status = 'overdue'
        days_late = (now.date() - issue.due_date.date()).days
        
        # Check if student already got notified today
        existing_student_notif = Notification.query.filter(
            Notification.recipient_type == 'student',
            Notification.recipient_id == issue.student_id,
            Notification.title.like(f"%Overdue: {issue.book.title[:20]}%")
        ).first()

        if not existing_student_notif:
            create_notification(
                recipient_type='student',
                recipient_id=issue.student_id,
                title=f"⚠️ Overdue: {issue.book.title}",
                message=f"The book '{issue.book.title}' was due on {issue.due_date.strftime('%Y-%m-%d')} ({days_late} days ago). Please return it immediately to avoid accumulating late fines.",
                notif_type='danger',
                link='/student/my-books'
            )
            
    db.session.commit()

def process_reservation_queue_on_return(book_id):
    """
    When a book is returned, check if there are pending reservations in queue.
    If yes, mark the next reservation as 'notified', set notified_at to now,
    and send a notification to the student that their reserved book is now ready for pickup.
    """
    next_res = Reservation.query.filter_by(
        book_id=book_id,
        status='pending'
    ).order_by(Reservation.queue_position.asc(), Reservation.reservation_date.asc()).first()

    if next_res:
        next_res.status = 'notified'
        next_res.notified_at = datetime.utcnow()
        db.session.commit()

        # Send notification to student
        create_notification(
            recipient_type='student',
            recipient_id=next_res.student_id,
            title="🎉 Reserved Book Available!",
            message=f"Good news! The book '{next_res.book.title}' you reserved is now available at the library counter. Please collect it within 48 hours.",
            notif_type='success',
            link='/student/my-books'
        )

        # Notify librarian
        create_notification(
            recipient_type='librarian',
            recipient_id=None,
            title=f"Book Available for Reservation: {next_res.book.title}",
            message=f"Student {next_res.student.name} ({next_res.student.student_id}) has been notified to pick up '{next_res.book.title}'.",
            notif_type='info',
            link='/reservations'
        )

