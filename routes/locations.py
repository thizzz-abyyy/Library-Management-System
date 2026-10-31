import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from models import db
from models.models import (
    Book, Category, Floor, Section, Room, Rack, Shelf, BookLocation, Setting
)
from routes import librarian_or_admin_required
from services.log_service import log_activity
from services.qr_service import generate_book_qr

locations_bp = Blueprint('locations', __name__, url_prefix='/locations')

# ==========================================
# 1. FIND A BOOK LOCATION
# ==========================================

@locations_bp.route('/find')
def find_book():
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    floor_id = request.args.get('floor', type=int)

    books_query = Book.query

    if search:
        books_query = books_query.filter(
            (Book.title.ilike(f"%{search}%")) |
            (Book.author.ilike(f"%{search}%")) |
            (Book.isbn.ilike(f"%{search}%")) |
            (Book.id == (int(search) if search.isdigit() else -1))
        )

    if category_id:
        books_query = books_query.filter_by(category_id=category_id)

    books = books_query.order_by(Book.title.asc()).all()

    # Filter by floor if requested
    if floor_id:
        filtered_books = []
        for b in books:
            match = False
            for loc in b.locations:
                if loc.shelf and loc.shelf.rack and loc.shelf.rack.room and loc.shelf.rack.room.floor_id == floor_id:
                    match = True
                    break
            if match:
                filtered_books.append(b)
        books = filtered_books

    categories = Category.query.order_by(Category.name.asc()).all()
    floors = Floor.query.order_by(Floor.floor_number.asc()).all()

    return render_template(
        'locations/find_book.html',
        books=books,
        categories=categories,
        floors=floors,
        search=search,
        selected_category=category_id,
        selected_floor=floor_id
    )


# ==========================================
# 2. VISUAL SHELF MAP
# ==========================================

@locations_bp.route('/map')
def visual_map():
    floors = Floor.query.order_by(Floor.floor_number.asc()).all()
    
    # Selected filters (or defaults)
    selected_floor_id = request.args.get('floor', type=int)
    selected_room_id = request.args.get('room', type=int)
    selected_rack_id = request.args.get('rack', type=int)
    selected_shelf_id = request.args.get('shelf', type=int)

    if not selected_floor_id and floors:
        selected_floor_id = floors[0].id

    current_floor = Floor.query.get(selected_floor_id) if selected_floor_id else None
    rooms = Room.query.filter_by(floor_id=selected_floor_id).all() if selected_floor_id else []

    if not selected_room_id and rooms:
        selected_room_id = rooms[0].id

    current_room = Room.query.get(selected_room_id) if selected_room_id else None
    racks = Rack.query.filter_by(room_id=selected_room_id).all() if selected_room_id else []

    if not selected_rack_id and racks:
        selected_rack_id = racks[0].id

    current_rack = Rack.query.get(selected_rack_id) if selected_rack_id else None
    shelves = Shelf.query.filter_by(rack_id=selected_rack_id).all() if selected_rack_id else []

    selected_shelf = Shelf.query.get(selected_shelf_id) if selected_shelf_id else (shelves[0] if shelves else None)

    return render_template(
        'locations/visual_map.html',
        floors=floors,
        current_floor=current_floor,
        rooms=rooms,
        current_room=current_room,
        racks=racks,
        current_rack=current_rack,
        shelves=shelves,
        selected_shelf=selected_shelf
    )


# ==========================================
# 3. SHELF & INFRASTRUCTURE MANAGEMENT
# ==========================================

@locations_bp.route('/shelves', methods=['GET', 'POST'])
@librarian_or_admin_required
def manage_shelves():
    if request.method == 'POST':
        action = request.form.get('action')

        # Floor Actions
        if action == 'add_floor':
            f_num = request.form.get('floor_number', type=int)
            f_name = request.form.get('name', '').strip()
            f_desc = request.form.get('description', '').strip()
            if f_num is not None and f_name:
                if Floor.query.filter_by(floor_number=f_num).first():
                    flash(f'Floor number {f_num} already exists.', 'danger')
                else:
                    new_floor = Floor(floor_number=f_num, name=f_name, description=f_desc)
                    db.session.add(new_floor)
                    db.session.commit()
                    log_activity('Add Floor', f"Added library floor '{f_name}' (#{f_num})")
                    flash(f"Floor '{f_name}' added successfully.", 'success')

        elif action == 'delete_floor':
            f_id = request.form.get('id', type=int)
            floor = Floor.query.get_or_404(f_id)
            if floor.rooms.count() > 0 or floor.sections.count() > 0:
                flash(f"Cannot delete floor '{floor.name}' because it contains registered rooms or sections.", 'danger')
            else:
                db.session.delete(floor)
                db.session.commit()
                flash(f"Floor '{floor.name}' deleted.", 'info')

        # Section Actions
        elif action == 'add_section':
            s_name = request.form.get('name', '').strip()
            s_code = request.form.get('code', '').strip().upper()
            s_floor = request.form.get('floor_id', type=int)
            s_desc = request.form.get('description', '').strip()
            if s_name and s_code and s_floor:
                if Section.query.filter_by(code=s_code).first():
                    flash(f"Section code '{s_code}' already exists.", 'danger')
                else:
                    sec = Section(name=s_name, code=s_code, floor_id=s_floor, description=s_desc)
                    db.session.add(sec)
                    db.session.commit()
                    log_activity('Add Section', f"Added library section '{s_name}' ({s_code})")
                    flash(f"Section '{s_name}' added.", 'success')

        # Room Actions
        elif action == 'add_room':
            r_num = request.form.get('room_number', '').strip()
            r_name = request.form.get('name', '').strip()
            r_floor = request.form.get('floor_id', type=int)
            r_sec = request.form.get('section_id', type=int)
            if r_num and r_floor:
                room = Room(room_number=r_num, name=r_name, floor_id=r_floor, section_id=r_sec or None)
                db.session.add(room)
                db.session.commit()
                log_activity('Add Room', f"Added room '{r_num}' ({r_name})")
                flash(f"Room '{r_num}' added.", 'success')

        # Rack Actions
        elif action == 'add_rack':
            rk_num = request.form.get('rack_number', '').strip()
            rk_room = request.form.get('room_id', type=int)
            rk_sec = request.form.get('section_id', type=int)
            rk_desc = request.form.get('description', '').strip()
            if rk_num and rk_room:
                rack = Rack(rack_number=rk_num, room_id=rk_room, section_id=rk_sec or None, description=rk_desc)
                db.session.add(rack)
                db.session.commit()
                log_activity('Add Rack', f"Added rack '{rk_num}'")
                flash(f"Rack '{rk_num}' added.", 'success')

        # Shelf Actions
        elif action == 'add_shelf':
            sh_num = request.form.get('shelf_number', '').strip()
            sh_rack = request.form.get('rack_id', type=int)
            sh_cap = request.form.get('capacity', 25, type=int)
            if sh_num and sh_rack:
                shelf = Shelf(shelf_number=sh_num, rack_id=sh_rack, capacity=max(1, sh_cap))
                db.session.add(shelf)
                db.session.commit()
                log_activity('Add Shelf', f"Added shelf '{sh_num}' with capacity {sh_cap}")
                flash(f"Shelf '{sh_num}' added.", 'success')

        elif action == 'edit_shelf':
            sh_id = request.form.get('id', type=int)
            shelf = Shelf.query.get_or_404(sh_id)
            shelf.shelf_number = request.form.get('shelf_number', shelf.shelf_number).strip()
            shelf.capacity = request.form.get('capacity', shelf.capacity, type=int)
            db.session.commit()
            flash(f"Shelf '{shelf.shelf_number}' updated.", 'success')

        elif action == 'delete_shelf':
            sh_id = request.form.get('id', type=int)
            shelf = Shelf.query.get_or_404(sh_id)
            if shelf.assigned_books_count > 0:
                flash(f"Cannot delete shelf '{shelf.shelf_number}' because it has {shelf.assigned_books_count} books assigned. Please reassign them first.", 'danger')
            else:
                name = shelf.shelf_number
                db.session.delete(shelf)
                db.session.commit()
                log_activity('Delete Shelf', f"Deleted empty shelf '{name}'")
                flash(f"Empty shelf '{name}' removed successfully.", 'info')

        # Assign Book Copy to Shelf
        elif action == 'assign_book':
            book_id = request.form.get('book_id', type=int)
            copy_number = request.form.get('copy_number', 1, type=int)
            shelf_id = request.form.get('shelf_id', type=int)
            pos_code = request.form.get('position_code', '').strip().upper()
            barcode_input = request.form.get('barcode', '').strip()
            notes = request.form.get('notes', '').strip()

            book = Book.query.get_or_404(book_id)
            shelf = Shelf.query.get_or_404(shelf_id)

            # Check shelf capacity
            if shelf.available_capacity <= 0:
                flash(f"Shelf '{shelf.shelf_number}' is at maximum capacity ({shelf.capacity} books).", 'danger')
                return redirect(url_for('locations.manage_shelves'))

            barcode_val = barcode_input or f"BC-BK{book.id:04d}-C{copy_number:02d}"

            # Check if this physical copy already has a location record
            existing_loc = BookLocation.query.filter_by(book_id=book.id, copy_number=copy_number).first()
            if existing_loc:
                existing_loc.shelf_id = shelf.id
                existing_loc.position_code = pos_code
                existing_loc.status = 'on_shelf'
                if barcode_input:
                    existing_loc.barcode = barcode_val
                existing_loc.last_confirmed_at = datetime.utcnow()
                if notes:
                    existing_loc.notes = notes
            else:
                new_loc = BookLocation(
                    book_id=book.id,
                    copy_number=copy_number,
                    barcode=barcode_val,
                    shelf_id=shelf.id,
                    position_code=pos_code,
                    status='on_shelf',
                    notes=notes
                )
                db.session.add(new_loc)

            # Update book shelf location summary
            book.shelf_location = f"{shelf.shelf_number} ({pos_code})"
            db.session.commit()

            # Re-generate book QR with location path
            try:
                book.qr_code_image = generate_book_qr(
                    book.id, book.isbn, book.title, book.author,
                    location_path=book.primary_location_display
                )
                db.session.commit()
            except Exception:
                pass

            log_activity('Assign Book Shelf', f"Assigned '{book.title}' Copy #{copy_number} to {shelf.full_location_path} (Pos: {pos_code})")
            flash(f"Book '{book.title}' (Copy #{copy_number}) assigned to {shelf.full_location_path} -> Pos {pos_code}.", 'success')

        return redirect(url_for('locations.manage_shelves'))

    # Load all entities for management view
    floors = Floor.query.order_by(Floor.floor_number.asc()).all()
    sections = Section.query.order_by(Section.name.asc()).all()
    rooms = Room.query.order_by(Room.room_number.asc()).all()
    racks = Rack.query.order_by(Rack.rack_number.asc()).all()
    shelves = Shelf.query.order_by(Shelf.id.asc()).all()
    books = Book.query.order_by(Book.title.asc()).all()
    locations = BookLocation.query.order_by(desc(BookLocation.last_confirmed_at)).limit(25).all()

    # Metrics
    total_floors = len(floors)
    total_sections = len(sections)
    total_racks = len(racks)
    total_shelves = len(shelves)
    total_located_books = BookLocation.query.filter(BookLocation.shelf_id.isnot(None)).count()
    unassigned_books = Book.query.filter(~Book.id.in_(db.session.query(BookLocation.book_id))).count()

    return render_template(
        'locations/shelves.html',
        floors=floors,
        sections=sections,
        rooms=rooms,
        racks=racks,
        shelves=shelves,
        books=books,
        locations=locations,
        total_floors=total_floors,
        total_sections=total_sections,
        total_racks=total_racks,
        total_shelves=total_shelves,
        total_located_books=total_located_books,
        unassigned_books=unassigned_books
    )


# ==========================================
# 4. QR SCANNER FOR LOCATION TRACKING
# ==========================================

@locations_bp.route('/scan')
def scan_location():
    """Interactive scanner dedicated to locating physical books."""
    return render_template('locations/scan.html')


# ==========================================
# 5. API ENDPOINTS
# ==========================================

@locations_bp.route('/api/lookup')
def api_lookup():
    """Returns exact physical location payload for scanned book QR, ISBN, or Book ID."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'found': False, 'message': 'No query specified'})

    book = None
    # Check if ID
    if q.isdigit():
        book = Book.query.get(int(q))
    if not book:
        book = Book.query.filter_by(isbn=q).first()
    if not book:
        # Check barcode in book_locations
        loc_record = BookLocation.query.filter_by(barcode=q).first()
        if loc_record:
            book = loc_record.book

    if not book:
        return jsonify({'found': False, 'message': 'Book not found'})

    copy_locations = []
    for loc in book.locations:
        copy_locations.append({
            'copy_number': loc.copy_number,
            'barcode': loc.barcode,
            'status': loc.status,
            'position_code': loc.position_code,
            'location_path': loc.full_location_display,
            'shelf_id': loc.shelf_id,
            'floor_name': loc.shelf.rack.room.floor.name if loc.shelf and loc.shelf.rack and loc.shelf.rack.room and loc.shelf.rack.room.floor else "N/A",
            'room_number': loc.shelf.rack.room.room_number if loc.shelf and loc.shelf.rack and loc.shelf.rack.room else "N/A",
            'rack_number': loc.shelf.rack.rack_number if loc.shelf and loc.shelf.rack else "N/A",
            'shelf_number': loc.shelf.shelf_number if loc.shelf else "N/A"
        })

    return jsonify({
        'found': True,
        'book': {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn,
            'category': book.category_name,
            'total_copies': book.total_copies,
            'available_copies': book.available_copies,
            'is_available': book.is_available,
            'cover_image': book.cover_image,
            'primary_location': book.primary_location_display,
            'copies': copy_locations
        }
    })


@locations_bp.route('/confirm-reshelve/<int:location_id>', methods=['POST'])
@librarian_or_admin_required
def confirm_reshelve(location_id):
    """Allows librarians to confirm physical re-shelving of returned books."""
    loc = BookLocation.query.get_or_404(location_id)
    loc.status = 'on_shelf'
    loc.last_confirmed_at = datetime.utcnow()
    db.session.commit()

    log_activity('Confirm Re-Shelve', f"Confirmed physical shelf placement for {loc.book.title} (Copy #{loc.copy_number}) at {loc.full_location_display}")
    flash(f"Physical placement confirmed for '{loc.book.title}' (Copy #{loc.copy_number}) on shelf.", 'success')
    return redirect(request.referrer or url_for('locations.manage_shelves'))
