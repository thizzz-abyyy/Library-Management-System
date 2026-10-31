import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from models import db
from models.models import (
    Admin, Librarian, Student, Category, Book, BookIssue,
    BookReturn, Reservation, Fine, Setting, Review, ActivityLog,
    Floor, Section, Room, Rack, Shelf, BookLocation
)
from services.qr_service import generate_book_qr, generate_student_qr

def seed_database():
    """Seeds initial records if database is fresh."""
    # 1. Settings
    default_settings = [
        ('library_name', 'Apex Central Digital Library', 'Official institution library title'),
        ('contact_email', 'library@apex.edu', 'Helpdesk contact email'),
        ('phone_number', '+1 (555) 019-2834', 'Circulation desk telephone'),
        ('address', '100 University Avenue, Tech Campus, Building B', 'Physical campus address'),
        ('currency_symbol', '$', 'Default monetary currency symbol'),
        ('fine_per_day', '1.00', 'Late return fine amount charged per day'),
        ('issue_duration_days', '14', 'Default loan period in days'),
        ('max_books_per_student', '3', 'Maximum simultaneous books allowed per student'),
        ('reservation_hold_hours', '48', 'Hours to hold reserved book before release')
    ]
    for key, val, desc in default_settings:
        if not Setting.query.filter_by(key=key).first():
            Setting.set(key, val, desc)

    # 2. Admin
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            name='Dr. Alistair Vance',
            email='admin@apex.edu'
        )
        admin.set_password('admin123')
        db.session.add(admin)

    # 3. Librarians
    if not Librarian.query.filter_by(librarian_id='LIB-001').first():
        lib1 = Librarian(
            librarian_id='LIB-001',
            name='Eleanor Rigby',
            email='librarian@apex.edu',
            phone='+1-555-0101',
            permissions='books,issues,returns,reservations,students,fines,reports',
            status='active'
        )
        lib1.set_password('librarian123')
        db.session.add(lib1)

    if not Librarian.query.filter_by(librarian_id='LIB-002').first():
        lib2 = Librarian(
            librarian_id='LIB-002',
            name='Marcus Holloway',
            email='marcus.h@apex.edu',
            phone='+1-555-0102',
            permissions='books,issues,returns,reservations',
            status='active'
        )
        lib2.set_password('librarian123')
        db.session.add(lib2)

    # 4. Categories
    categories_data = [
        ('Computer Science & Software', 'Algorithms, architecture, data structures, and programming paradigms.', 'bi-laptop'),
        ('Artificial Intelligence & ML', 'Machine learning, neural networks, deep learning, and intelligent agents.', 'bi-cpu'),
        ('Database & Systems Design', 'Relational models, distributed data architectures, and SQL engines.', 'bi-database'),
        ('Mathematics & Statistics', 'Calculus, linear algebra, discrete math, and probability.', 'bi-calculator'),
        ('Electronics & Robotics', 'Embedded systems, microcontrollers, circuits, and sensors.', 'bi-motherboard'),
        ('Business & Management', 'Technology entrepreneurship, project leadership, and organizational psychology.', 'bi-briefcase')
    ]
    cat_map = {}
    for name, desc, icon in categories_data:
        cat = Category.query.filter_by(name=name).first()
        if not cat:
            cat = Category(name=name, description=desc, icon=icon)
            db.session.add(cat)
            db.session.flush()
        cat_map[name] = cat.id

    # 5. Students
    students_data = [
        ('STU-2026-001', 'Alexander Hayes', 'Computer Science & Engineering', 'Final Year (2025-2026)', 'student@apex.edu', '+1-555-0201', 'Room 304, Redwood Hall, Campus'),
        ('STU-2026-002', 'Sophia Chen', 'Data Science & AI', '3rd Year', 'sophia.c@apex.edu', '+1-555-0202', '742 Evergreen Terrace, North District'),
        ('STU-2026-003', 'Liam O\'Connor', 'Mechanical Engineering', '2nd Year', 'liam.oc@apex.edu', '+1-555-0203', 'Flat 12, Parkside Apartments'),
        ('STU-2026-004', 'Emily Rodriguez', 'Electrical & Electronics', 'Final Year (2025-2026)', 'emily.r@apex.edu', '+1-555-0204', 'Room 112, Magnolia Residence')
    ]
    student_objs = {}
    for sid, sname, dept, year, email, phone, addr in students_data:
        stu = Student.query.filter_by(student_id=sid).first()
        if not stu:
            stu = Student(
                student_id=sid,
                name=sname,
                department=dept,
                academic_year=year,
                email=email,
                phone=phone,
                address=addr,
                status='active'
            )
            stu.set_password('student123')
            try:
                stu.qr_code_image = generate_student_qr(sid, sname, dept)
            except Exception:
                pass
            db.session.add(stu)
            db.session.flush()
        student_objs[sid] = stu

    # 6. Books
    books_data = [
        ('978-0132350884', 'Clean Code: A Handbook of Agile Software Craftsmanship', 'Robert C. Martin', 'Prentice Hall', 'Computer Science & Software', 2008, 5, 4, 'Shelf CS-01', 'Even bad code can function. But if code isn\'t clean, it can bring a development organization to its knees.'),
        ('978-0262033848', 'Introduction to Algorithms (CLRS)', 'Thomas H. Cormen et al.', 'MIT Press', 'Computer Science & Software', 2009, 8, 7, 'Shelf CS-02', 'Comprehensive textbook covering depth and rigor across algorithm design, dynamic programming, graph theory, and complexity analysis.'),
        ('978-0134685991', 'Effective Java (3rd Edition)', 'Joshua Bloch', 'Addison-Wesley Professional', 'Computer Science & Software', 2018, 4, 3, 'Shelf CS-03', 'Definitive guide to Java best practices, design patterns, and modern idiomatic programming.'),
        ('978-0262035613', 'Deep Learning', 'Ian Goodfellow, Yoshua Bengio, Aaron Courville', 'MIT Press', 'Artificial Intelligence & ML', 2016, 6, 5, 'Shelf AI-01', 'An introduction to mathematical and conceptual foundations of deep learning architectures and neural optimization.'),
        ('978-1449369415', 'Designing Data-Intensive Applications', 'Martin Kleppmann', 'O\'Reilly Media', 'Database & Systems Design', 2017, 7, 6, 'Shelf DB-01', 'The definitive guide to the architecture of reliable, scalable, and maintainable distributed data systems.'),
        ('978-0131103627', 'The C Programming Language (2nd Edition)', 'Brian W. Kernighan, Dennis M. Ritchie', 'Prentice Hall', 'Computer Science & Software', 1988, 5, 5, 'Shelf CS-04', 'The classic authoritative guide to C programming language by its creators.'),
        ('978-1491957660', 'Hands-On Machine Learning with Scikit-Learn and TensorFlow', 'Aurélien Géron', 'O\'Reilly Media', 'Artificial Intelligence & ML', 2019, 5, 4, 'Shelf AI-02', 'Through a series of recent breakthroughs, deep learning has boosted the entire field of machine learning.'),
        ('978-0321125217', 'Domain-Driven Design: Tackling Complexity in Software', 'Eric Evans', 'Addison-Wesley', 'Computer Science & Software', 2003, 3, 2, 'Shelf CS-05', 'Systematic approach to software design connecting an implementation to an evolving model.')
    ]
    book_objs = {}
    for isbn, title, author, pub, cat_name, yr, total, avail, shelf, desc in books_data:
        bk = Book.query.filter_by(isbn=isbn).first()
        if not bk:
            bk = Book(
                isbn=isbn,
                title=title,
                author=author,
                publisher=pub,
                category_id=cat_map.get(cat_name),
                publication_year=yr,
                total_copies=total,
                available_copies=avail,
                shelf_location=shelf,
                description=desc
            )
            db.session.add(bk)
            db.session.flush()
            try:
                bk.qr_code_image = generate_book_qr(bk.id, isbn, title, author)
            except Exception:
                pass
        book_objs[isbn] = bk

    db.session.commit()

    # 7. Sample Issues, Returns, Fines, Reservations, Reviews
    if BookIssue.query.count() == 0:
        now = datetime.utcnow()
        # Active Issue
        b1 = book_objs.get('978-0132350884')
        s1 = student_objs.get('STU-2026-001')
        if b1 and s1:
            iss1 = BookIssue(
                issue_code='ISS-2026-0001',
                book_id=b1.id,
                student_id=s1.id,
                issued_by_type='admin',
                issued_by_id=1,
                issue_date=now - timedelta(days=5),
                due_date=now + timedelta(days=9),
                status='issued',
                notes='Standard checkout'
            )
            db.session.add(iss1)

        # Overdue Issue
        b5 = book_objs.get('978-1449369415')
        s2 = student_objs.get('STU-2026-002')
        if b5 and s2:
            iss2 = BookIssue(
                issue_code='ISS-2026-0002',
                book_id=b5.id,
                student_id=s2.id,
                issued_by_type='librarian',
                issued_by_id=1,
                issue_date=now - timedelta(days=20),
                due_date=now - timedelta(days=6),
                status='overdue',
                notes='System marked overdue'
            )
            db.session.add(iss2)

        # Returned Issue with Paid Fine
        b2 = book_objs.get('978-0262033848')
        s3 = student_objs.get('STU-2026-003')
        if b2 and s3:
            iss3 = BookIssue(
                issue_code='ISS-2026-0003',
                book_id=b2.id,
                student_id=s3.id,
                issued_by_type='librarian',
                issued_by_id=1,
                issue_date=now - timedelta(days=16),
                due_date=now - timedelta(days=2),
                return_date=now,
                status='returned',
                notes='Returned with late fee'
            )
            db.session.add(iss3)
            db.session.flush()

            ret1 = BookReturn(
                issue_id=iss3.id,
                book_id=b2.id,
                student_id=s3.id,
                received_by_type='librarian',
                received_by_id=1,
                return_date=now,
                overdue_days=2,
                fine_amount=2.00,
                condition_notes='Returned in excellent condition'
            )
            db.session.add(ret1)

            fine1 = Fine(
                issue_id=iss3.id,
                student_id=s3.id,
                amount=2.00,
                overdue_days=2,
                status='paid',
                payment_date=now,
                payment_method='Cash',
                transaction_id='RCPT-10042',
                notes='Paid at circulation counter.'
            )
            db.session.add(fine1)

        # Pending Reservation
        b8 = book_objs.get('978-0321125217')
        if b8 and s1:
            res1 = Reservation(
                reservation_code='RES-2026-0001',
                book_id=b8.id,
                student_id=s1.id,
                reservation_date=now - timedelta(days=1),
                status='pending',
                queue_position=1
            )
            db.session.add(res1)

        # Reviews
        if b1 and s1:
            r1 = Review(
                book_id=b1.id,
                student_id=s1.id,
                rating=5,
                review_text='A transformative read for any aspiring software developer. Completely changed how I write methods and structure classes.'
            )
            db.session.add(r1)

        if b5 and s2:
            r2 = Review(
                book_id=b5.id,
                student_id=s2.id,
                rating=5,
                review_text='Hands down the best technology book ever written on distributed systems and database internals!'
            )
            db.session.add(r2)

        # Initial Log
        log = ActivityLog(
            user_type='system',
            action='System Initialization',
            details='Initialized seed data, admin, librarians, students, and catalog.',
            ip_address='127.0.0.1'
        )
        db.session.add(log)
        db.session.commit()

    # 8. Seed Smart Floors, Sections, Rooms, Racks, Shelves, and Book Locations (Unconditional check)
    seed_shelf_locations(book_objs)
    db.session.commit()


def seed_shelf_locations(book_objs=None):
    """Initializes library physical infrastructure and assigns books to shelves."""
    if Floor.query.count() == 0:
        # Floors
        f0 = Floor(floor_number=0, name="Ground Floor", description="Main Circulation, Engineering & Computing Archives")
        f1 = Floor(floor_number=1, name="First Floor", description="Artificial Intelligence, Data Science & Mathematics Wing")
        f2 = Floor(floor_number=2, name="Second Floor", description="Research Periodicals, Business & Postgraduate Archives")
        db.session.add_all([f0, f1, f2])
        db.session.flush()

        # Sections
        s_cs = Section(name="Computer Science", code="SEC-CS", floor_id=f0.id, description="Software systems, programming, algorithms")
        s_db = Section(name="Database & Systems Design", code="SEC-DB", floor_id=f0.id, description="Relational data, distributed architectures")
        s_ai = Section(name="Artificial Intelligence & ML", code="SEC-AI", floor_id=f1.id, description="Machine learning, robotics, deep learning")
        s_math = Section(name="Mathematics & Statistics", code="SEC-MATH", floor_id=f1.id, description="Linear algebra, calculus, discrete math")
        s_bus = Section(name="Business & Management", code="SEC-BUS", floor_id=f2.id, description="Technology leadership, innovation management")
        db.session.add_all([s_cs, s_db, s_ai, s_math, s_bus])
        db.session.flush()

        # Rooms
        r101 = Room(room_number="Room 101", name="Main Computing Archives", floor_id=f0.id, section_id=s_cs.id)
        r102 = Room(room_number="Room 102", name="Database & Systems Hall", floor_id=f0.id, section_id=s_db.id)
        r201 = Room(room_number="Room 201", name="Advanced AI & Data Lab", floor_id=f1.id, section_id=s_ai.id)
        r202 = Room(room_number="Room 202", name="Quantitative Science Wing", floor_id=f1.id, section_id=s_math.id)
        db.session.add_all([r101, r102, r201, r202])
        db.session.flush()

        # Racks
        rk_r05 = Rack(rack_number="Rack R05", room_id=r101.id, section_id=s_cs.id, description="Software Engineering & Agile Methodologies")
        rk_r01 = Rack(rack_number="Rack R01", room_id=r101.id, section_id=s_cs.id, description="Programming Languages & Compilers")
        rk_r02 = Rack(rack_number="Rack R02", room_id=r102.id, section_id=s_db.id, description="Distributed Storage & Database Internals")
        rk_r03 = Rack(rack_number="Rack R03", room_id=r201.id, section_id=s_ai.id, description="Neural Networks & Deep Learning Research")
        db.session.add_all([rk_r05, rk_r01, rk_r02, rk_r03])
        db.session.flush()

        # Shelves
        sh_s01 = Shelf(shelf_number="Shelf S01", rack_id=rk_r05.id, capacity=25)
        sh_s02 = Shelf(shelf_number="Shelf S02", rack_id=rk_r05.id, capacity=25)
        sh_s03 = Shelf(shelf_number="Shelf S03", rack_id=rk_r05.id, capacity=30)
        sh_s04 = Shelf(shelf_number="Shelf S04", rack_id=rk_r05.id, capacity=25)

        sh_r01_s01 = Shelf(shelf_number="Shelf S01", rack_id=rk_r01.id, capacity=25)
        sh_r01_s02 = Shelf(shelf_number="Shelf S02", rack_id=rk_r01.id, capacity=25)

        sh_r02_s01 = Shelf(shelf_number="Shelf S01", rack_id=rk_r02.id, capacity=30)
        sh_r02_s02 = Shelf(shelf_number="Shelf S02", rack_id=rk_r02.id, capacity=30)

        sh_r03_s01 = Shelf(shelf_number="Shelf S01", rack_id=rk_r03.id, capacity=30)
        sh_r03_s02 = Shelf(shelf_number="Shelf S02", rack_id=rk_r03.id, capacity=30)
        db.session.add_all([sh_s01, sh_s02, sh_s03, sh_s04, sh_r01_s01, sh_r01_s02, sh_r02_s01, sh_r02_s02, sh_r03_s01, sh_r03_s02])
        db.session.flush()

        db.session.commit()

    # Assign physical locations for all books and copies if not already assigned
    if BookLocation.query.count() == 0:
        # Retrieve primary shelves
        shelf_s03 = Shelf.query.filter_by(shelf_number="Shelf S03").first()
        shelf_s02 = Shelf.query.filter_by(shelf_number="Shelf S02").first()
        shelf_s01 = Shelf.query.filter_by(shelf_number="Shelf S01").first()

        books = Book.query.all()
        for b in books:
            # Match prompt requirement:
            # Example: Clean Code -> Ground Floor -> Computer Science -> Room 101 -> Rack R05 -> Shelf S03 -> Position B12
            target_shelf = shelf_s03 if b.id == 1 else (shelf_s02 if b.id % 2 == 0 else shelf_s01)
            
            for copy_i in range(1, b.total_copies + 1):
                pos = f"B{11 + copy_i}" if b.id == 1 else f"Pos-{copy_i:02d}"
                status = 'issued' if (copy_i > b.available_copies) else 'on_shelf'
                
                loc = BookLocation(
                    book_id=b.id,
                    copy_number=copy_i,
                    barcode=f"BC-BK{b.id:04d}-C{copy_i:02d}",
                    shelf_id=target_shelf.id if target_shelf else None,
                    position_code=pos,
                    status=status,
                    notes=f"Physical inventory copy #{copy_i}"
                )
                db.session.add(loc)

        db.session.commit()

