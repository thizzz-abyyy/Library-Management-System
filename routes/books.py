import os
import uuid
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import desc
from models import db
from models.models import Book, Category, Review, BookIssue, Setting
from routes import librarian_or_admin_required
from services.qr_service import generate_book_qr
from services.log_service import log_activity
from services.recommendation_service import get_related_books

books_bp = Blueprint('books', __name__, url_prefix='/books')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']


@books_bp.route('/')
def list_books():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    availability = request.args.get('availability', '')

    query = Book.query

    if search:
        query = query.filter(
            (Book.title.ilike(f"%{search}%")) |
            (Book.author.ilike(f"%{search}%")) |
            (Book.isbn.ilike(f"%{search}%")) |
            (Book.publisher.ilike(f"%{search}%"))
        )

    if category_id:
        query = query.filter_by(category_id=category_id)

    if availability == 'available':
        query = query.filter(Book.available_copies > 0)
    elif availability == 'unavailable':
        query = query.filter(Book.available_copies == 0)

    books_paginated = query.order_by(desc(Book.created_at)).paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.order_by(Category.name.asc()).all()

    return render_template(
        'books/list.html',
        books=books_paginated,
        categories=categories,
        search=search,
        selected_category=category_id,
        selected_availability=availability
    )


@books_bp.route('/<int:book_id>')
def details(book_id):
    book = Book.query.get_or_404(book_id)
    related = get_related_books(book, limit=4)
    recent_issues = BookIssue.query.filter_by(book_id=book.id).order_by(desc(BookIssue.issue_date)).limit(5).all()
    reviews = Review.query.filter_by(book_id=book.id).order_by(desc(Review.created_at)).all()
    currency = Setting.get('currency_symbol', '$')

    return render_template(
        'books/details.html',
        book=book,
        related=related,
        recent_issues=recent_issues,
        reviews=reviews,
        currency=currency
    )


@books_bp.route('/add', methods=['GET', 'POST'])
@librarian_or_admin_required
def add():
    if request.method == 'POST':
        isbn = request.form.get('isbn', '').strip()
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        publisher = request.form.get('publisher', '').strip()
        category_id = request.form.get('category_id', type=int)
        publication_year = request.form.get('publication_year', type=int)
        total_copies = request.form.get('total_copies', 1, type=int)
        shelf_location = request.form.get('shelf_location', '').strip()
        description = request.form.get('description', '').strip()

        if not all([isbn, title, author]):
            flash('ISBN, Title, and Author are required fields.', 'warning')
            return redirect(url_for('books.add'))

        if Book.query.filter_by(isbn=isbn).first():
            flash('A book with this ISBN already exists.', 'danger')
            return redirect(url_for('books.add'))

        cover_filename = 'default_book_cover.png'
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename != '' and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                cover_filename = f"cover_{uuid.uuid4().hex[:10]}.{ext}"
                file.save(os.path.join(current_app.config['BOOK_COVERS_FOLDER'], cover_filename))

        new_book = Book(
            isbn=isbn,
            title=title,
            author=author,
            publisher=publisher,
            category_id=category_id,
            publication_year=publication_year,
            total_copies=max(1, total_copies),
            available_copies=max(1, total_copies),
            shelf_location=shelf_location,
            description=description,
            cover_image=cover_filename
        )
        db.session.add(new_book)
        db.session.flush() # get ID for QR generation

        # Auto-generate QR code
        qr_file = generate_book_qr(new_book.id, isbn, title, author)
        new_book.qr_code_image = qr_file

        db.session.commit()

        log_activity('Add Book', f"Added book '{title}' (ISBN: {isbn}) with {total_copies} copies")
        flash(f"Book '{title}' added successfully with QR Code generated!", 'success')
        return redirect(url_for('books.details', book_id=new_book.id))

    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('books/add_edit.html', action='add', book=None, categories=categories)


@books_bp.route('/<int:book_id>/edit', methods=['GET', 'POST'])
@librarian_or_admin_required
def edit(book_id):
    book = Book.query.get_or_404(book_id)

    if request.method == 'POST':
        isbn = request.form.get('isbn', '').strip()
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        publisher = request.form.get('publisher', '').strip()
        category_id = request.form.get('category_id', type=int)
        publication_year = request.form.get('publication_year', type=int)
        new_total_copies = request.form.get('total_copies', book.total_copies, type=int)
        shelf_location = request.form.get('shelf_location', '').strip()
        description = request.form.get('description', '').strip()

        # Check unique ISBN if changed
        if isbn != book.isbn and Book.query.filter_by(isbn=isbn).first():
            flash('Another book with this ISBN already exists.', 'danger')
            return redirect(url_for('books.edit', book_id=book.id))

        # Adjust available copies if total changed
        copies_diff = new_total_copies - book.total_copies
        new_available = max(0, book.available_copies + copies_diff)

        book.isbn = isbn
        book.title = title
        book.author = author
        book.publisher = publisher
        book.category_id = category_id
        book.publication_year = publication_year
        book.total_copies = new_total_copies
        book.available_copies = new_available
        book.shelf_location = shelf_location
        book.description = description

        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename != '' and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                cover_filename = f"cover_{uuid.uuid4().hex[:10]}.{ext}"
                file.save(os.path.join(current_app.config['BOOK_COVERS_FOLDER'], cover_filename))
                book.cover_image = cover_filename

        # Regenerate QR Code
        qr_file = generate_book_qr(book.id, isbn, title, author)
        book.qr_code_image = qr_file

        db.session.commit()
        log_activity('Edit Book', f"Updated details for '{title}' (ID: {book.id})")
        flash(f"Book '{title}' updated successfully.", 'success')
        return redirect(url_for('books.details', book_id=book.id))

    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('books/add_edit.html', action='edit', book=book, categories=categories)


@books_bp.route('/<int:book_id>/delete', methods=['POST'])
@librarian_or_admin_required
def delete(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if there are active issues
    active_issues = BookIssue.query.filter_by(book_id=book.id, status='issued').count()
    if active_issues > 0:
        flash(f"Cannot delete '{book.title}' because {active_issues} cop(ies) are currently issued.", 'danger')
        return redirect(url_for('books.details', book_id=book.id))

    title = book.title
    db.session.delete(book)
    db.session.commit()
    
    log_activity('Delete Book', f"Deleted book '{title}' (ID: {book_id})")
    flash(f"Book '{title}' was deleted successfully.", 'info')
    return redirect(url_for('books.list_books'))


# ==========================================
# CATEGORIES MANAGEMENT
# ==========================================

@books_bp.route('/categories', methods=['GET', 'POST'])
@librarian_or_admin_required
def categories():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name', '').strip()
            desc = request.form.get('description', '').strip()
            icon = request.form.get('icon', 'bi-bookmark').strip()
            
            if not name:
                flash('Category name is required.', 'warning')
            elif Category.query.filter_by(name=name).first():
                flash('Category already exists.', 'danger')
            else:
                cat = Category(name=name, description=desc, icon=icon)
                db.session.add(cat)
                db.session.commit()
                log_activity('Add Category', f"Created category '{name}'")
                flash(f"Category '{name}' created successfully.", 'success')

        elif action == 'edit':
            cat_id = request.form.get('id')
            cat = Category.query.get_or_404(cat_id)
            cat.name = request.form.get('name', '').strip()
            cat.description = request.form.get('description', '').strip()
            cat.icon = request.form.get('icon', 'bi-bookmark').strip()
            db.session.commit()
            flash(f"Category '{cat.name}' updated.", 'success')

        elif action == 'delete':
            cat_id = request.form.get('id')
            cat = Category.query.get_or_404(cat_id)
            name = cat.name
            db.session.delete(cat)
            db.session.commit()
            flash(f"Category '{name}' removed.", 'info')

        return redirect(url_for('books.categories'))

    categories_list = Category.query.order_by(Category.name.asc()).all()
    return render_template('books/categories.html', categories=categories_list)


@books_bp.route('/api/search')
def api_search():
    """Returns quick search JSON results for live autocomplete / QR scanner lookup."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    
    books = Book.query.filter(
        (Book.title.ilike(f"%{q}%")) |
        (Book.isbn.ilike(f"%{q}%")) |
        (Book.id == (int(q) if q.isdigit() else -1))
    ).limit(8).all()

    return jsonify([{
        'id': b.id,
        'isbn': b.isbn,
        'title': b.title,
        'author': b.author,
        'available_copies': b.available_copies,
        'is_available': b.is_available,
        'cover': b.cover_image
    } for b in books])

