from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db

class UserSession(UserMixin):
    """Unified user adapter for Flask-Login across Admin, Librarian, and Student tables."""
    def __init__(self, user_obj, role):
        self.user_obj = user_obj
        self.role = role # 'admin', 'librarian', or 'student'
        self.id = f"{role}_{user_obj.id}"
        self.raw_id = user_obj.id
        self.name = getattr(user_obj, 'name', 'User')
        self.email = getattr(user_obj, 'email', '')
        self.avatar = getattr(user_obj, 'avatar', 'default_avatar.png')
        self.status = getattr(user_obj, 'status', 'active')
        
    def get_id(self):
        return self.id

    def has_permission(self, perm):
        if self.role == 'admin':
            return True
        if self.role == 'librarian':
            perms = [p.strip() for p in getattr(self.user_obj, 'permissions', '').split(',') if p.strip()]
            return 'all' in perms or perm in perms
        return False


class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Librarian(db.Model):
    __tablename__ = 'librarians'

    id = db.Column(db.Integer, primary_key=True)
    librarian_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    permissions = db.Column(db.Text, default='books,issues,returns,reservations,students,fines,reports')
    status = db.Column(db.String(20), default='active', index=True) # 'active', 'inactive'
    avatar = db.Column(db.String(255), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(32), unique=True, nullable=False, index=True) # e.g. STU-2026-001
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(100), nullable=False, index=True)
    academic_year = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text)
    avatar = db.Column(db.String(255), default='default_avatar.png')
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='active', index=True) # 'active', 'suspended'
    qr_code_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    issues = db.relationship('BookIssue', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    returns = db.relationship('BookReturn', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    reservations = db.relationship('Reservation', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    fines = db.relationship('Fine', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def active_issues_count(self):
        return self.issues.filter_by(status='issued').count()

    @property
    def pending_fines_total(self):
        pending = self.fines.filter_by(status='pending').all()
        return sum(float(f.amount) for f in pending)


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='bi-bookmark')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    books = db.relationship('Book', backref='category_rel', lazy='dynamic')
    ebooks = db.relationship('EBook', backref='category_rel', lazy='dynamic')


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    author = db.Column(db.String(255), nullable=False, index=True)
    publisher = db.Column(db.String(255))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)
    publication_year = db.Column(db.Integer)
    total_copies = db.Column(db.Integer, default=1, nullable=False)
    available_copies = db.Column(db.Integer, default=1, nullable=False)
    shelf_location = db.Column(db.String(64))
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(255), default='default_book_cover.png')
    qr_code_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    issues = db.relationship('BookIssue', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    returns = db.relationship('BookReturn', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    reservations = db.relationship('Reservation', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    locations = db.relationship('BookLocation', backref='book', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_available(self):
        return self.available_copies > 0

    @property
    def average_rating(self):
        revs = self.reviews.all()
        if not revs:
            return 0.0
        return round(sum(r.rating for r in revs) / len(revs), 1)

    @property
    def category_name(self):
        return self.category_rel.name if self.category_rel else 'Uncategorized'

    @property
    def primary_location(self):
        return self.locations.order_by(BookLocation.copy_number.asc()).first()

    @property
    def primary_location_display(self):
        loc = self.primary_location
        if loc and loc.shelf:
            return loc.full_location_display
        if self.shelf_location:
            return f"Shelf: {self.shelf_location}"
        return "Unassigned (Pending Shelf Placement)"


class BookIssue(db.Model):
    __tablename__ = 'book_issues'

    id = db.Column(db.Integer, primary_key=True)
    issue_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    issued_by_type = db.Column(db.String(20), default='admin') # 'admin' or 'librarian'
    issued_by_id = db.Column(db.Integer)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False, index=True)
    return_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='issued', index=True) # 'issued', 'returned', 'overdue'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    return_record = db.relationship('BookReturn', backref='issue', uselist=False, cascade='all, delete-orphan')
    fines = db.relationship('Fine', backref='issue', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_overdue(self):
        if self.status == 'returned':
            return False
        return datetime.utcnow() > self.due_date

    @property
    def overdue_days(self):
        if self.status == 'returned' and self.return_date:
            diff = (self.return_date.date() - self.due_date.date()).days
            return max(0, diff)
        diff = (datetime.utcnow().date() - self.due_date.date()).days
        return max(0, diff)


class BookReturn(db.Model):
    __tablename__ = 'book_returns'

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('book_issues.id', ondelete='CASCADE'), nullable=False, unique=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    received_by_type = db.Column(db.String(20), default='admin')
    received_by_id = db.Column(db.Integer)
    return_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    overdue_days = db.Column(db.Integer, default=0)
    fine_amount = db.Column(db.Numeric(10, 2), default=0.00)
    condition_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    reservation_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    reservation_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='pending', index=True) # 'pending', 'notified', 'fulfilled', 'cancelled', 'expired'
    queue_position = db.Column(db.Integer, default=1)
    notified_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Fine(db.Model):
    __tablename__ = 'fines'

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('book_issues.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    overdue_days = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending', index=True) # 'pending', 'paid', 'waived'
    payment_date = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50)) # 'Cash', 'Card', 'Online', 'Waived'
    transaction_id = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    recipient_type = db.Column(db.String(20), nullable=False, index=True) # 'student', 'librarian', 'admin', 'all'
    recipient_id = db.Column(db.Integer, nullable=True, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='info') # 'info', 'warning', 'success', 'danger'
    is_read = db.Column(db.Boolean, default=False, index=True)
    link = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class EBook(db.Model):
    __tablename__ = 'ebooks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    author = db.Column(db.String(255), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255), nullable=False)
    cover_image = db.Column(db.String(255), default='default_ebook_cover.png')
    file_size_mb = db.Column(db.Numeric(8, 2), default=0.00)
    downloads_count = db.Column(db.Integer, default=0)
    views_count = db.Column(db.Integer, default=0)
    is_downloadable = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    review_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20), nullable=False, index=True) # 'admin', 'librarian', 'student', 'system'
    user_id = db.Column(db.Integer)
    user_name = db.Column(db.String(120))
    action = db.Column(db.String(120), nullable=False, index=True)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=''):
        item = cls.query.filter_by(key=key).first()
        return item.value if item else default

    @classmethod
    def set(cls, key, value, description=None):
        item = cls.query.filter_by(key=key).first()
        if not item:
            item = cls(key=key, value=str(value), description=description)
            db.session.add(item)
        else:
            item.value = str(value)
            if description:
                item.description = description
        db.session.commit()


# ==========================================
# SMART BOOK SHELF & LOCATION TRACKING MODELS
# ==========================================

class Floor(db.Model):
    __tablename__ = 'floors'

    id = db.Column(db.Integer, primary_key=True)
    floor_number = db.Column(db.Integer, unique=True, nullable=False, index=True) # e.g. 0, 1, 2
    name = db.Column(db.String(100), nullable=False) # e.g. "Ground Floor", "First Floor - Science Wing"
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sections = db.relationship('Section', backref='floor', lazy='dynamic', cascade='all, delete-orphan')
    rooms = db.relationship('Room', backref='floor', lazy='dynamic', cascade='all, delete-orphan')


class Section(db.Model):
    __tablename__ = 'sections'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True) # e.g. "Computer Science & Engineering"
    code = db.Column(db.String(32), unique=True, nullable=False, index=True) # e.g. "SEC-CS"
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id', ondelete='CASCADE'), nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    rooms = db.relationship('Room', backref='section', lazy='dynamic')
    racks = db.relationship('Rack', backref='section', lazy='dynamic')


class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(50), nullable=False, index=True) # e.g. "Room 101"
    name = db.Column(db.String(100)) # e.g. "Main Computing Archives"
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id', ondelete='CASCADE'), nullable=False, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id', ondelete='SET NULL'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    racks = db.relationship('Rack', backref='room', lazy='dynamic', cascade='all, delete-orphan')


class Rack(db.Model):
    __tablename__ = 'racks'

    id = db.Column(db.Integer, primary_key=True)
    rack_number = db.Column(db.String(50), nullable=False, index=True) # e.g. "Rack R01", "Rack R05"
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id', ondelete='SET NULL'), nullable=True, index=True)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    shelves = db.relationship('Shelf', backref='rack', lazy='dynamic', cascade='all, delete-orphan')


class Shelf(db.Model):
    __tablename__ = 'shelves'

    id = db.Column(db.Integer, primary_key=True)
    shelf_number = db.Column(db.String(50), nullable=False, index=True) # e.g. "Shelf S01", "Shelf S03"
    rack_id = db.Column(db.Integer, db.ForeignKey('racks.id', ondelete='CASCADE'), nullable=False, index=True)
    capacity = db.Column(db.Integer, default=25, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    book_locations = db.relationship('BookLocation', backref='shelf', lazy='dynamic')

    @property
    def assigned_books_count(self):
        return self.book_locations.count()

    @property
    def available_capacity(self):
        return max(0, self.capacity - self.assigned_books_count)

    @property
    def occupancy_percent(self):
        if self.capacity <= 0:
            return 100
        return min(100, round((self.assigned_books_count / self.capacity) * 100))

    @property
    def full_location_path(self):
        floor_name = self.rack.room.floor.name if self.rack and self.rack.room and self.rack.room.floor else "Unknown Floor"
        section_name = self.rack.section.name if self.rack and self.rack.section else (self.rack.room.section.name if self.rack and self.rack.room and self.rack.room.section else "General")
        room_num = self.rack.room.room_number if self.rack and self.rack.room else "Room"
        rack_num = self.rack.rack_number if self.rack else "Rack"
        return f"{floor_name} → {section_name} → {room_num} → {rack_num} → {self.shelf_number}"


class BookLocation(db.Model):
    __tablename__ = 'book_locations'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False, index=True)
    copy_number = db.Column(db.Integer, default=1, nullable=False)
    barcode = db.Column(db.String(64), unique=True, index=True)
    shelf_id = db.Column(db.Integer, db.ForeignKey('shelves.id', ondelete='SET NULL'), nullable=True, index=True)
    position_code = db.Column(db.String(32)) # e.g. "B12", "Pos-01"
    status = db.Column(db.String(20), default='on_shelf', index=True) # 'on_shelf', 'issued', 'reserved', 'maintenance'
    last_confirmed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def full_location_display(self):
        if not self.shelf:
            return "Unassigned (Pending Shelf Placement)"
        base_path = self.shelf.full_location_path
        pos = f" → Position {self.position_code}" if self.position_code else ""
        return f"{base_path}{pos}"


