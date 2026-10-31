import os
import uuid
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from models import db
from models.models import EBook, Category
from routes import librarian_or_admin_required
from services.log_service import log_activity

ebooks_bp = Blueprint('ebooks', __name__, url_prefix='/ebooks')

def allowed_ebook(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EBOOK_EXTENSIONS']

def allowed_cover(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']


@ebooks_bp.route('/')
def list_ebooks():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)

    query = EBook.query
    if search:
        query = query.filter(
            (EBook.title.ilike(f"%{search}%")) |
            (EBook.author.ilike(f"%{search}%")) |
            (EBook.description.ilike(f"%{search}%"))
        )
    if category_id:
        query = query.filter_by(category_id=category_id)

    ebooks_paginated = query.order_by(desc(EBook.created_at)).paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.order_by(Category.name.asc()).all()

    return render_template(
        'ebooks/list.html',
        ebooks=ebooks_paginated,
        categories=categories,
        search=search,
        selected_category=category_id
    )


@ebooks_bp.route('/add', methods=['GET', 'POST'])
@librarian_or_admin_required
def add():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        category_id = request.form.get('category_id', type=int)
        description = request.form.get('description', '').strip()
        is_downloadable = bool(request.form.get('is_downloadable', True))

        if not title or not author:
            flash('Title and Author are required.', 'warning')
            return redirect(url_for('ebooks.add'))

        if 'ebook_file' not in request.files:
            flash('Please choose an e-book file (PDF).', 'warning')
            return redirect(url_for('ebooks.add'))

        file = request.files['ebook_file']
        if file.filename == '' or not allowed_ebook(file.filename):
            flash('Valid PDF or EPUB file is required.', 'danger')
            return redirect(url_for('ebooks.add'))

        # Save ebook file safely
        ext = file.filename.rsplit('.', 1)[1].lower()
        ebook_filename = f"ebook_{uuid.uuid4().hex[:12]}.{ext}"
        save_path = os.path.join(current_app.config['EBOOKS_FOLDER'], ebook_filename)
        file.save(save_path)
        
        file_size_mb = round(os.path.getsize(save_path) / (1024 * 1024), 2)

        # Handle cover image
        cover_filename = 'default_ebook_cover.png'
        if 'cover_image' in request.files:
            cover_file = request.files['cover_image']
            if cover_file and cover_file.filename != '' and allowed_cover(cover_file.filename):
                cover_ext = cover_file.filename.rsplit('.', 1)[1].lower()
                cover_filename = f"ebook_cover_{uuid.uuid4().hex[:8]}.{cover_ext}"
                cover_file.save(os.path.join(current_app.config['BOOK_COVERS_FOLDER'], cover_filename))

        new_ebook = EBook(
            title=title,
            author=author,
            category_id=category_id,
            description=description,
            file_path=ebook_filename,
            cover_image=cover_filename,
            file_size_mb=file_size_mb,
            is_downloadable=is_downloadable
        )
        db.session.add(new_ebook)
        db.session.commit()

        log_activity('Upload E-Book', f"Uploaded digital e-book '{title}' by {author} ({file_size_mb} MB)")
        flash(f"E-Book '{title}' uploaded successfully!", 'success')
        return redirect(url_for('ebooks.list_ebooks'))

    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('ebooks/add.html', categories=categories)


@ebooks_bp.route('/<int:ebook_id>/read')
@login_required
def read(ebook_id):
    """Secure in-browser reader for authenticated users."""
    ebook = EBook.query.get_or_404(ebook_id)
    ebook.views_count += 1
    db.session.commit()

    return render_template('ebooks/viewer.html', ebook=ebook)


@ebooks_bp.route('/<int:ebook_id>/file')
@login_required
def serve_file(ebook_id):
    """Serves the actual PDF binary to authorized viewer."""
    ebook = EBook.query.get_or_404(ebook_id)
    return send_from_directory(current_app.config['EBOOKS_FOLDER'], ebook.file_path)


@ebooks_bp.route('/<int:ebook_id>/download')
@login_required
def download(ebook_id):
    ebook = EBook.query.get_or_404(ebook_id)
    if not ebook.is_downloadable and current_user.role == 'student':
        flash('This e-book is restricted to in-browser reading only.', 'warning')
        return redirect(url_for('ebooks.read', ebook_id=ebook.id))

    ebook.downloads_count += 1
    db.session.commit()

    log_activity('Download E-Book', f"User {current_user.name} downloaded '{ebook.title}'")
    return send_from_directory(
        current_app.config['EBOOKS_FOLDER'],
        ebook.file_path,
        as_attachment=True,
        download_name=f"{ebook.title}.pdf"
    )


@ebooks_bp.route('/<int:ebook_id>/delete', methods=['POST'])
@librarian_or_admin_required
def delete(ebook_id):
    ebook = EBook.query.get_or_404(ebook_id)
    title = ebook.title
    
    # Remove file from disk
    file_on_disk = Path(current_app.config['EBOOKS_FOLDER']) / ebook.file_path
    if file_on_disk.exists():
        try:
            os.remove(file_on_disk)
        except Exception:
            pass

    db.session.delete(ebook)
    db.session.commit()

    log_activity('Delete E-Book', f"Deleted digital e-book '{title}'")
    flash(f"E-Book '{title}' removed successfully.", 'info')
    return redirect(url_for('ebooks.list_ebooks'))

