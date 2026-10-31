from sqlalchemy import func, desc
from models import db
from models.models import Book, BookIssue, Review, Category

def get_recommendations_for_student(student_id, limit=6):
    """
    AI/Heuristic Hybrid Recommendation Engine:
    1. Student Category Affinity (based on past issues)
    2. Co-borrowing collaborative signals (books borrowed by peers with overlapping interests)
    3. Popularity & High rating reinforcement
    """
    recommended_books = []
    seen_book_ids = set()

    # 1. Get IDs of books the student has already borrowed
    borrowed_issues = BookIssue.query.filter_by(student_id=student_id).all()
    borrowed_book_ids = {issue.book_id for issue in borrowed_issues}
    seen_book_ids.update(borrowed_book_ids)

    # 2. Category Affinity: Find top categories borrowed by this student
    if borrowed_book_ids:
        top_categories = db.session.query(
            Book.category_id,
            func.count(Book.category_id).label('cat_count')
        ).join(BookIssue, BookIssue.book_id == Book.id)\
         .filter(BookIssue.student_id == student_id, Book.category_id.isnot(None))\
         .group_by(Book.category_id)\
         .order_by(desc('cat_count')).limit(3).all()

        fav_category_ids = [cat[0] for cat in top_categories]

        if fav_category_ids:
            cat_books = Book.query.filter(
                Book.category_id.in_(fav_category_ids),
                ~Book.id.in_(seen_book_ids)
            ).order_by(desc(Book.total_copies)).limit(limit // 2).all()

            for b in cat_books:
                if b.id not in seen_book_ids:
                    recommended_books.append(b)
                    seen_book_ids.add(b.id)

    # 3. Collaborative Co-borrowing: Find books borrowed by students who borrowed similar books
    if borrowed_book_ids:
        peer_student_ids = [
            row[0] for row in db.session.query(BookIssue.student_id)
            .filter(BookIssue.book_id.in_(borrowed_book_ids), BookIssue.student_id != student_id)
            .distinct().limit(20).all()
        ]

        if peer_student_ids:
            co_borrowed = db.session.query(
                Book,
                func.count(BookIssue.id).label('issue_count')
            ).join(BookIssue, BookIssue.book_id == Book.id)\
             .filter(BookIssue.student_id.in_(peer_student_ids), ~Book.id.in_(seen_book_ids))\
             .group_by(Book.id)\
             .order_by(desc('issue_count')).limit(3).all()

            for b, _ in co_borrowed:
                if b.id not in seen_book_ids:
                    recommended_books.append(b)
                    seen_book_ids.add(b.id)

    # 4. Fill remaining with Most Popular Books (most borrowed overall)
    remaining_needed = limit - len(recommended_books)
    if remaining_needed > 0:
        popular_books = db.session.query(
            Book,
            func.count(BookIssue.id).label('pop_count')
        ).outerjoin(BookIssue, BookIssue.book_id == Book.id)\
         .filter(~Book.id.in_(seen_book_ids))\
         .group_by(Book.id)\
         .order_by(desc('pop_count'), desc(Book.created_at))\
         .limit(remaining_needed).all()

        for b, _ in popular_books:
            if b.id not in seen_book_ids:
                recommended_books.append(b)
                seen_book_ids.add(b.id)

    # 5. Fallback if still empty: latest available books
    if len(recommended_books) < limit:
        extra = Book.query.filter(~Book.id.in_(seen_book_ids))\
                    .order_by(desc(Book.created_at))\
                    .limit(limit - len(recommended_books)).all()
        recommended_books.extend(extra)

    return recommended_books

def get_related_books(book, limit=4):
    """
    Returns related books by same category, author, or tags.
    """
    if not book:
        return []
    
    query = Book.query.filter(Book.id != book.id)
    if book.category_id:
        query = query.filter(
            (Book.category_id == book.category_id) | (Book.author == book.author)
        )
    else:
        query = query.filter(Book.author == book.author)
        
    return query.order_by(desc(Book.created_at)).limit(limit).all()

