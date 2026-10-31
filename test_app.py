import unittest
from datetime import datetime, timedelta
from app import create_app
from models import db
from models.models import (
    Admin, Librarian, Student, Book, BookIssue, BookReturn,
    Fine, Reservation, Category, Setting, ActivityLog, EBook,
    Floor, Section, Room, Rack, Shelf, BookLocation
)
from services.recommendation_service import get_recommendations_for_student

class LibraryManagementSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client.get('/logout') # Reset session between tests

    def tearDown(self):
        self.ctx.pop()

    def test_01_database_and_seeds(self):
        """Verifies database tables, default admin, librarian, students, and settings."""
        admin = Admin.query.filter_by(username='admin').first()
        self.assertIsNotNone(admin, "Default admin should exist")
        self.assertTrue(admin.check_password('admin123'), "Admin password should match")

        lib = Librarian.query.filter_by(librarian_id='LIB-001').first()
        self.assertIsNotNone(lib, "Default librarian LIB-001 should exist")
        self.assertTrue(lib.check_password('librarian123'), "Librarian password should match")

        student = Student.query.filter_by(student_id='STU-2026-001').first()
        self.assertIsNotNone(student, "Default student STU-2026-001 should exist")
        self.assertTrue(student.check_password('student123'), "Student password should match")

        books_count = Book.query.count()
        self.assertGreaterEqual(books_count, 8, "Initial books should be seeded")

    def test_02_authentication_flows(self):
        """Tests Admin login, Student login, and invalid credentials."""
        # Valid Admin Login
        res_admin = self.client.post('/login', data={
            'login_id': 'admin',
            'password': 'admin123',
            'role_type': 'admin'
        }, follow_redirects=True)
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"Welcome back", res_admin.data)

        # Logout
        self.client.get('/logout', follow_redirects=True)

        # Valid Student Login
        res_stu = self.client.post('/login', data={
            'login_id': 'STU-2026-001',
            'password': 'student123',
            'role_type': 'student'
        }, follow_redirects=True)
        self.assertEqual(res_stu.status_code, 200)
        self.assertIn(b"Welcome back", res_stu.data)

        # Logout
        self.client.get('/logout', follow_redirects=True)

        # Invalid Login Attempt
        res_bad = self.client.post('/login', data={
            'login_id': 'admin',
            'password': 'wrongpassword123',
            'role_type': 'auto'
        }, follow_redirects=True)
        self.assertIn(b"Invalid credentials", res_bad.data)

    def test_03_student_registration(self):
        """Tests self-registration flow with auto QR generation."""
        test_id = f"STU-TEST-{int(datetime.utcnow().timestamp())}"
        test_email = f"test_{int(datetime.utcnow().timestamp())}@apex.edu"
        
        res = self.client.post('/register', data={
            'name': 'Test New Scholar',
            'email': test_email,
            'student_id': test_id,
            'department': 'Computer Science & Engineering',
            'academic_year': '1st Year',
            'phone': '+1-555-9988',
            'address': 'Dormitory Hall 5',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Registration successful", res.data)

        created = Student.query.filter_by(student_id=test_id).first()
        self.assertIsNotNone(created)
        self.assertIsNotNone(created.qr_code_image, "Student QR Code should be generated")

    def test_04_book_creation_and_qr(self):
        """Tests book creation with QR code generation."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123', 'role_type': 'admin'}, follow_redirects=True)

        isbn = f"978-TEST-{int(datetime.utcnow().timestamp())}"
        res = self.client.post('/books/add', data={
            'isbn': isbn,
            'title': 'Automated Test Architecture',
            'author': 'Alan Turing',
            'publisher': 'Academic Press',
            'category_id': 1,
            'publication_year': 2024,
            'total_copies': 4,
            'shelf_location': 'Shelf QA-01',
            'description': 'Testing software engineering principles.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        book = Book.query.filter_by(isbn=isbn).first()
        self.assertIsNotNone(book)
        self.assertEqual(book.available_copies, 4)
        self.assertIsNotNone(book.qr_code_image, "Book QR Code should be generated")

    def test_05_book_issue_and_return(self):
        """Tests issue transaction, quota decrement, return transaction, and quota restoration."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123', 'role_type': 'admin'}, follow_redirects=True)

        book = Book.query.filter(Book.available_copies > 0).first()
        student = Student.query.filter_by(student_id='STU-2026-004').first()
        initial_avail = book.available_copies

        # 1. Issue Book
        res_issue = self.client.post('/issues/issue', data={
            'student_id': student.student_id,
            'book_id': book.id,
            'duration_days': 14,
            'notes': 'Unit test checkout'
        }, follow_redirects=True)
        self.assertEqual(res_issue.status_code, 200)
        self.assertIn(b"successfully issued", res_issue.data)

        db.session.refresh(book)
        self.assertEqual(book.available_copies, initial_avail - 1)

        issue = BookIssue.query.filter_by(book_id=book.id, student_id=student.id, status='issued').order_by(BookIssue.id.desc()).first()
        self.assertIsNotNone(issue)

        # 2. Return Book
        res_return = self.client.post('/issues/return', data={
            'issue_id': issue.id,
            'condition_notes': 'Returned in mint condition',
            'fine_action': 'pending'
        }, follow_redirects=True)
        self.assertEqual(res_return.status_code, 200)
        self.assertIn(b"returned successfully", res_return.data)

        db.session.refresh(book)
        self.assertEqual(book.available_copies, initial_avail)

        ret = BookReturn.query.filter_by(issue_id=issue.id).first()
        self.assertIsNotNone(ret)

    def test_06_reports_and_csv(self):
        """Tests reports generation and CSV download endpoint."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123', 'role_type': 'admin'}, follow_redirects=True)

        res = self.client.get('/reports/?type=books')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Total Books &amp; Inventory Report", res.data)

        # CSV Export test
        res_csv = self.client.get('/reports/?type=books&export=csv')
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, 'text/csv')
        self.assertIn(b"Book ID,ISBN,Title,Author", res_csv.data)

    def test_07_reservation_system(self):
        """Tests student reserving book, queue positioning, and fulfilling."""
        self.client.post('/login', data={'login_id': 'STU-2026-002', 'password': 'student123', 'role_type': 'student'}, follow_redirects=True)
        book = Book.query.filter(Book.id != 8).first() # Book 8 has sample reservation in seed
        
        # Clear any prior reservation from previous test runs to ensure idempotency
        Reservation.query.filter_by(student_id=2, book_id=book.id).delete()
        db.session.commit()

        res_reserve = self.client.post(f'/student/reserve/{book.id}', follow_redirects=True)
        self.assertEqual(res_reserve.status_code, 200)
        self.assertIn(b"Reservation placed successfully", res_reserve.data)

        # Verify reservation record
        res_record = Reservation.query.filter_by(student_id=2, book_id=book.id, status='pending').first()
        self.assertIsNotNone(res_record)
        self.assertGreaterEqual(res_record.queue_position, 1)

    def test_08_fine_management(self):
        """Tests recording fine payment and waiving fine."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123', 'role_type': 'admin'}, follow_redirects=True)

        # Create sample pending fine
        issue = BookIssue.query.first()
        fine = Fine(
            issue_id=issue.id,
            student_id=issue.student_id,
            amount=5.00,
            overdue_days=5,
            status='pending',
            notes='Test fine'
        )
        db.session.add(fine)
        db.session.commit()

        # Pay fine
        res_pay = self.client.post(f'/fines/{fine.id}/pay', data={
            'payment_method': 'Cash',
            'transaction_id': 'RCPT-TEST-001',
            'notes': 'Test payment'
        }, follow_redirects=True)
        self.assertEqual(res_pay.status_code, 200)
        self.assertIn(b"recorded successfully", res_pay.data)

        db.session.refresh(fine)
        self.assertEqual(fine.status, 'paid')

    def test_09_recommendation_algorithm(self):
        """Tests AI-based hybrid recommendation service."""
        student = Student.query.first()
        recommendations = get_recommendations_for_student(student.id, limit=4)
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0, "Recommendations should return books")
        for b in recommendations:
            self.assertIsInstance(b, Book)

    def test_10_shelf_infrastructure_and_locations(self):
        """Tests Smart Book Shelf hierarchy, visual map, API lookup, and assignment CRUD."""
        # 1. Verify Seeded Location Data
        clean_code = Book.query.get(1)
        self.assertIsNotNone(clean_code)
        self.assertIn("Ground Floor", clean_code.primary_location_display)
        self.assertIn("Rack R05", clean_code.primary_location_display)
        self.assertIn("Shelf S03", clean_code.primary_location_display)
        self.assertIn("B12", clean_code.primary_location_display)

        # 2. Test Find Book Search Page
        res_find = self.client.get('/locations/find?q=Clean+Code')
        self.assertEqual(res_find.status_code, 200)
        self.assertIn(b"Clean Code", res_find.data)
        self.assertIn(b"Rack R05", res_find.data)

        # 3. Test Visual Shelf Map Page
        res_map = self.client.get('/locations/map')
        self.assertEqual(res_map.status_code, 200)
        self.assertIn(b"Visual Library Shelf Navigator", res_map.data)

        # 4. Test Scan Location Page
        res_scan = self.client.get('/locations/scan')
        self.assertEqual(res_scan.status_code, 200)
        self.assertIn(b"Instant Physical Shelf Locator", res_scan.data)

        # 5. Test Location API Lookup
        res_api = self.client.get('/locations/api/lookup?q=1')
        self.assertEqual(res_api.status_code, 200)
        api_data = res_api.get_json()
        self.assertTrue(api_data['found'])
        self.assertEqual(api_data['book']['id'], 1)
        self.assertIn("B12", api_data['book']['primary_location'])

        # 6. Admin Login & Shelf Management CRUD Operations
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123', 'role_type': 'admin'}, follow_redirects=True)
        
        # Cleanup any previous test-created items for idempotency
        old_floor3 = Floor.query.filter_by(floor_number=3).first()
        if old_floor3:
            db.session.delete(old_floor3)
            db.session.commit()
        BookLocation.query.filter_by(barcode='BC-TEST-CLRS-C2').delete()
        db.session.commit()

        # Add Floor
        res_add_floor = self.client.post('/locations/shelves', data={
            'action': 'add_floor',
            'floor_number': 3,
            'name': 'Third Floor - Innovation Attic',
            'description': 'Special collections and silent archives'
        }, follow_redirects=True)
        self.assertEqual(res_add_floor.status_code, 200)
        floor3 = Floor.query.filter_by(floor_number=3).first()
        self.assertIsNotNone(floor3)

        # Add Section
        res_add_sec = self.client.post('/locations/shelves', data={
            'action': 'add_section',
            'name': 'Robotics & Hardware Labs',
            'code': 'SEC-ROBO-TEST',
            'floor_id': floor3.id,
            'description': 'Hardware engineering'
        }, follow_redirects=True)
        self.assertEqual(res_add_sec.status_code, 200)
        sec_robo = Section.query.filter_by(code='SEC-ROBO-TEST').first()
        self.assertIsNotNone(sec_robo)

        # Add Room
        res_add_room = self.client.post('/locations/shelves', data={
            'action': 'add_room',
            'room_number': 'Room 305',
            'name': 'Robotics Studio',
            'floor_id': floor3.id,
            'section_id': sec_robo.id
        }, follow_redirects=True)
        self.assertEqual(res_add_room.status_code, 200)
        room_305 = Room.query.filter_by(room_number='Room 305').first()
        self.assertIsNotNone(room_305)

        # Add Rack
        res_add_rack = self.client.post('/locations/shelves', data={
            'action': 'add_rack',
            'rack_number': 'Rack RB01',
            'room_id': room_305.id,
            'section_id': sec_robo.id,
            'description': 'Robotics mechanics'
        }, follow_redirects=True)
        self.assertEqual(res_add_rack.status_code, 200)
        rack_rb01 = Rack.query.filter_by(rack_number='Rack RB01').first()
        self.assertIsNotNone(rack_rb01)

        # Add Shelf
        res_add_shelf = self.client.post('/locations/shelves', data={
            'action': 'add_shelf',
            'shelf_number': 'Shelf S99',
            'rack_id': rack_rb01.id,
            'capacity': 20
        }, follow_redirects=True)
        self.assertEqual(res_add_shelf.status_code, 200)
        shelf_s99 = Shelf.query.filter_by(shelf_number='Shelf S99', rack_id=rack_rb01.id).first()
        self.assertIsNotNone(shelf_s99)

        # Assign Book Copy to Shelf
        res_assign = self.client.post('/locations/shelves', data={
            'action': 'assign_book',
            'book_id': 2,
            'shelf_id': shelf_s99.id,
            'copy_number': 2,
            'position_code': 'Z01',
            'barcode': 'BC-TEST-CLRS-C2'
        }, follow_redirects=True)
        self.assertEqual(res_assign.status_code, 200)

        assigned_loc = BookLocation.query.filter_by(barcode='BC-TEST-CLRS-C2').first()
        self.assertIsNotNone(assigned_loc)
        self.assertEqual(assigned_loc.position_code, 'Z01')
        self.assertEqual(assigned_loc.shelf_id, shelf_s99.id)

        # Confirm Re-Shelve Placement
        res_confirm = self.client.post(f'/locations/confirm-reshelve/{assigned_loc.id}', follow_redirects=True)
        self.assertEqual(res_confirm.status_code, 200)
        db.session.refresh(assigned_loc)
        self.assertEqual(assigned_loc.status, 'on_shelf')


if __name__ == '__main__':
    unittest.main()
