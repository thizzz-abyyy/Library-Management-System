# 📚 Apex Central Library Management System

> **A Commercial-Grade, Full-Stack Digital Library Platform built with Python Flask, MySQL, Bootstrap 5, Chart.js, and QR Code Integration.**

---

## 🌟 Executive Summary

The **Apex Central Library Management System** is an enterprise-grade digital library web application designed to meet the rigorous requirements of institutional universities and academic libraries. Built using **Python (Flask Framework)** and **MySQL**, it features dedicated role-based portals for **Administrators**, **Librarians**, and **Students**.

The platform provides complete end-to-end management of academic assets: cataloging, real-time book loan issue and returns, automated late-fine accruals, queuing reservations, camera-based QR code scanning, digital PDF e-book reading, AI-powered book recommendations, audit logging, and reporting analytics with CSV exports.

---

## 🚀 Key Modules & System Features

### 1. 🛡️ Multi-Role Authentication & Access Control
- **Unified Login Portal**: Single, sleek login interface with automatic role detection across **Admin**, **Librarian**, and **Student** accounts.
- **Secure Password Hashing**: Utilizes **Werkzeug Scrypt** cryptographic password hashing.
- **Role-Based Access Control (RBAC)**: Custom decorators (`@admin_required`, `@librarian_or_admin_required`, `@student_required`) securing all internal endpoints.
- **Session Management**: Full Flask-Login session integration with persistent "Remember Me" support.

### 2. 📊 Executive Admin Dashboard
- **8 Dynamic KPI Counter Cards**:
  - Total Books (and unique catalog titles count)
  - Total Registered Students
  - Total Circulation Staff (Librarians)
  - Available Books on shelf
  - Currently Issued Books
  - Overdue Loans with alert status
  - Active Pending Reservations
  - Total Fine Collections (Paid Revenue vs Pending Receivables)
- **Interactive Chart.js Visualizations**:
  - **Monthly Circulation Trends**: Line chart comparing book checkouts and returns over the last 6 months.
  - **Category Breakdown**: Doughnut chart illustrating volume distribution across disciplines.
- **Operational Panels**:
  - Recent Book Checkouts table
  - Urgent Overdue Loans warning panel with quick-action return buttons
  - Most Popular Books leaderboard
  - Recently Cataloged Books list

### 3. 📖 Catalog & Book Management
- **Full CRUD Operations**: Add, inspect, update, and safely delete books.
- **Automated QR Code Generation**: Automatically creates high-resolution QR barcodes (via `qrcode` & `Pillow`) encoding book metadata (`ID`, `ISBN`, `Title`).
- **Real-Time Stock Availability**: Tracks `total_copies` vs `available_copies` with automated decrement on issue and increment on return.
- **Cover Image Uploads**: Secure file upload handler with validation and default fallback artwork.
- **Academic Classification**: Hierarchical category management with custom icons.

### 4. 📤 Circulation Desk: Issue & Return Management
- **Issue System**:
  - Searchable student roll number and book lookup with instant verification.
  - Automatically records issue date and calculates scheduled due date based on institutional policy (configurable, default 14 days).
  - Enforces borrowing quotas (e.g. max 3 books per student) and flags suspended accounts.
- **Return System**:
  - Fast search by Issue ID, Student ID, or Book QR code.
  - **Automated Fine Calculation**: Accurately computes late fees based on elapsed overdue days and the configured per-day fine rate.
  - **Overdue Settlement Workflow**: Direct options to mark fine as paid (with transaction receipt ID), record as pending, or waive.
  - **Reservation Queue Trigger**: Automatically alerts the next student in line when a reserved book is returned!

### 5. 📷 QR Code Camera Scanner Integration
- **Webcam QR Scanner**: Powered by `html5-qrcode` to scan book barcodes and student identity cards via device camera.
- Audio beep feedback and automatic form population for high-throughput circulation desk workflows.

### 6. 💰 Automated Fine & Penalty Management
- **Configurable Fine Rate**: Administrator can configure the daily late penalty in System Settings.
- **Fine Ledger**: Comprehensive table tracking pending dues, paid collections, and waived penalties.
- **Settlement Receipts**: Records transaction ID, payment method (Cash, Card, Online), and timestamp.

### 7. 🔖 Book Reservation & Queue System
- Students can place holds/reservations on high-demand or out-of-stock books.
- Automatically maintains strict FIFO queue ordering (`queue_position`).
- Notifies students via in-app alerts when their reserved volume is returned and holds it for a configurable pickup window (e.g., 48 hours).

### 8. 🎓 Dedicated Student Portal
- **Personalized Scholar Dashboard**:
  - Real-time loan counter, countdown to return dates, and fine balances.
  - My Borrowed Books table with status badges (`Active`, `Overdue`).
- **Printable Student Library ID Card**:
  - High-resolution student card with photo, roll number, department, validity, and scannable student QR barcode.
  - CSS print stylesheet (`@media print`) for one-click clean physical card printing.
- **Book Reviews & Star Ratings**:
  - Scholars can rate books from 1 to 5 stars and submit academic reviews.
- **In-App Notification Center**:
  - Automated alerts for upcoming due dates, overdue notices, and reservation readiness.

### 9. 🧠 AI-Based Book Recommendation Module
- **Hybrid Recommendation Algorithm**:
  1. **Category Affinity**: Analyzes scholar's borrowing history and favors topics in their curriculum.
  2. **Collaborative Filtering Signal**: Identifies co-borrowed titles read by peers with overlapping loans.
  3. **Popularity & Rating Weight**: Surfaces the most in-demand, highest-rated titles across the collection.

### 10. 📄 Digital E-Book Library & PDF Reader
- Secure repository for electronic textbooks and lecture materials.
- In-browser PDF reading interface with responsive reader view.
- Offline PDF download option with permission toggles and download tracking.

### 11. 📈 Reports & Analytics with CSV Export
- Generate institutional reports for:
  - Total Books & Catalog Inventory
  - Registered Students
  - Book Issue Transactions
  - Book Return Transactions
  - Overdue Delinquencies
  - Fine Collections & Revenue
  - Most Popular Titles
- Date range filtering, printable formatting, and one-click **Export to CSV**.

### 12. 📍 Smart Book Shelf & Physical Location Tracking System
- **Exact Stacks Geolocation**: Tracks every volume down to `Floor → Section → Room → Rack → Shelf → Position Slot` (e.g. *Ground Floor → Computer Science → Room 101 → Rack R05 → Shelf S03 → Position B12*).
- **Shelf Management (`/locations/shelves`)**: Full administrative CRUD for Floors, Sections, Rooms, Racks, and Shelves with capacity monitoring.
- **Find My Book (`/locations/find`)**: Instant catalog search revealing physical location breadcrumbs and map jump links.
- **Visual Shelf Map (`/locations/map`)**: Interactive multi-floor navigator with rack layouts, shelf occupancy gauges, and book assignment inspection.
- **QR Code Location Scanner (`/locations/scan`)**: Device camera scanner decoding physical location coordinates in real-time.
- **Re-Shelving Verification**: Returned books track shelf placement and require librarian physical confirmation.

### 13. 🔒 Security & Audit Logging
- Parameterized SQL queries via SQLAlchemy to prevent SQL injection.
- Session fixation protection and safe redirection.
- Centralized `ActivityLog` capturing user ID, role, action, details, timestamp, and client IP address.
- Database backup exporter (JSON snapshot download).

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.10+, Flask, Flask-Login, Flask-SQLAlchemy, Werkzeug |
| **Database** | MySQL (Primary via PyMySQL) with automatic SQLite fallback |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Visualization** | Chart.js 4.4 |
| **Media & QR** | QRCode, Pillow (PIL), HTML5-QRCode Scanner |
| **Configuration** | Python-Dotenv, PyMySQL, Cryptography |

---

## 📁 Project Directory Structure

```text
library_management/
├── api/
│   └── index.py                # Vercel serverless function entry point
├── app.py                      # Application factory, routes registration & error handlers
├── config.py                   # Environment configuration & dynamic DB connection resolver
├── init_db.py                  # Initial seed data generator & QR code populator
├── requirements.txt            # Python dependencies
├── vercel.json                 # Vercel routing & edge rewrites configuration
├── .gitignore                  # Production git ignore rules
├── test_app.py                 # Comprehensive automated test suite (10 test suites)
├── .env.example                # Sample environment variables
├── .env                        # Local active environment configuration
│
├── models/
│   ├── __init__.py             # SQLAlchemy db instance
│   └── models.py               # 19 relational tables, physical shelf hierarchy & user sessions
│
├── routes/
│   ├── __init__.py             # Role-based security decorators
│   ├── auth.py                 # Login, student registration, logout, role dispatching
│   ├── admin.py                # Admin dashboard, librarian CRUD, activity logs, settings
│   ├── books.py                # Book catalog, add/edit, categories, search API
│   ├── students.py             # Student records, ID card generator, live student search
│   ├── issues.py               # Issue desk, return desk, QR lookup API
│   ├── fines.py                # Fine collection ledger, payment processing, waiving
│   ├── reservations.py         # Reservation queue management & fulfillment
│   ├── ebooks.py               # Digital e-book library, secure PDF viewer & download
│   ├── locations.py            # Smart Shelf Management, Visual Map, Search & QR Locator
│   ├── student.py              # Student portal, my books, reviews, profile, notifications
│   └── reports.py              # Reporting engine, date filters, CSV generator
│
├── services/
│   ├── __init__.py
│   ├── qr_service.py           # QR code generation with Pillow & qrcode
│   ├── log_service.py          # Centralized audit activity logging
│   ├── notification_service.py # In-app notification creation & overdue scanner
│   └── recommendation_service.py # AI hybrid recommendation algorithm
│
├── database/
│   └── library.sql             # Complete MySQL DDL script with 13 tables & sample data
│
├── templates/
│   ├── base.html               # Master layout with sidebar, navbar, Dark Mode & modals
│   ├── index.html              # Public landing page with catalog explorer & featured books
│   ├── auth/                   # Login & registration templates
│   ├── admin/                  # Dashboard, librarians, logs, settings
│   ├── books/                  # Catalog list, add/edit, book details with reviews
│   ├── students/               # Student list, add/edit, student details, printable ID card
│   ├── issues/                 # Issue book, return book, circulation history
│   ├── reservations/           # Reservation queue list
│   ├── fines/                  # Fine ledger
│   ├── ebooks/                 # E-book catalog, upload, reader view
│   ├── reports/                # Report dashboard & printable ledger
│   ├── student_portal/         # Student dashboard, my books, history, fines, recommendations
│   └── components/             # 404 & 500 error pages
│
├── static/
│   ├── css/style.css           # Custom theme stylesheet (Light/Dark mode, print styles)
│   ├── js/main.js              # Theme switcher, sidebar toggle, modal helpers
│   ├── js/charts.js            # Chart.js initialization for circulation trends
│   └── js/qr_scanner.js        # Camera barcode/QR scanner integration
│
└── uploads/
    ├── book_covers/            # Uploaded book cover images
    ├── qr_codes/               # Generated book and student QR barcodes
    ├── ebooks/                 # Uploaded PDF files
    └── avatars/                # Scholar profile photos
```

---

## 🗄️ Database Design (13 MySQL Tables)

The database schema is defined in `database/library.sql` and mirrored in SQLAlchemy models:

1. **`admins`**: System administrators (`id`, `username`, `name`, `email`, `password_hash`, `avatar`, `created_at`).
2. **`librarians`**: Circulation staff (`id`, `librarian_id`, `name`, `email`, `phone`, `password_hash`, `permissions`, `status`, `created_at`).
3. **`students`**: Registered scholars (`id`, `student_id`, `name`, `department`, `academic_year`, `email`, `phone`, `address`, `avatar`, `password_hash`, `status`, `qr_code_image`, `created_at`).
4. **`categories`**: Book classifications (`id`, `name`, `description`, `icon`, `created_at`).
5. **`books`**: Physical volumes (`id`, `isbn`, `title`, `author`, `publisher`, `category_id`, `publication_year`, `total_copies`, `available_copies`, `shelf_location`, `description`, `cover_image`, `qr_code_image`, `created_at`).
6. **`book_issues`**: Checkout loans (`id`, `issue_code`, `book_id`, `student_id`, `issued_by_type`, `issued_by_id`, `issue_date`, `due_date`, `return_date`, `status`, `notes`).
7. **`book_returns`**: Return receipts (`id`, `issue_id`, `book_id`, `student_id`, `received_by_type`, `received_by_id`, `return_date`, `overdue_days`, `fine_amount`, `condition_notes`).
8. **`reservations`**: Queue holds (`id`, `reservation_code`, `book_id`, `student_id`, `reservation_date`, `status`, `queue_position`, `notified_at`, `notes`).
9. **`fines`**: Monetary penalties (`id`, `issue_id`, `student_id`, `amount`, `overdue_days`, `status`, `payment_date`, `payment_method`, `transaction_id`, `notes`).
10. **`notifications`**: In-app messages (`id`, `recipient_type`, `recipient_id`, `title`, `message`, `type`, `is_read`, `link`, `created_at`).
11. **`ebooks`**: Digital PDF repository (`id`, `title`, `author`, `category_id`, `description`, `file_path`, `cover_image`, `file_size_mb`, `downloads_count`, `views_count`, `is_downloadable`).
12. **`reviews`**: Ratings & critiques (`id`, `book_id`, `student_id`, `rating`, `review_text`, `created_at`).
13. **`activity_logs`**: System audit trail (`id`, `user_type`, `user_id`, `user_name`, `action`, `details`, `ip_address`, `created_at`).
14. **`settings`**: Dynamic system configuration (`id`, `key`, `value`, `description`, `updated_at`).

---

## 🔑 Default Demo Login Credentials

The system comes pre-seeded with ready-to-test accounts:

| Role | Username / ID | Password | Access Scope |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full control over all system modules, staff, settings & logs |
| **Librarian Staff** | `LIB-001` | `librarian123` | Book cataloging, circulation desk (issue/return), fines, reservations |
| **Student Scholar** | `STU-2026-001` | `student123` | Student portal, borrowed books, reservations, fines, ID card, AI picks |
| **Student Scholar 2** | `STU-2026-002` | `student123` | Secondary test student for co-borrowing & reservations |

> 💡 *On the login screen, you can click any of the "Quick Test Credentials" pill buttons to auto-populate the fields!*

---

## 💻 Installation & Setup Guide

### Option A: Instant Run (Zero Setup)
The application is pre-configured with intelligent auto-detection. If MySQL is not running locally, it seamlessly initializes the SQLite database with full sample data and QR codes so you can test it immediately without configuration:

```powershell
# 1. Install dependencies (if not already installed)
python -m pip install -r requirements.txt

# 2. Run the application
python app.py
```
Open your browser and navigate to: **`http://localhost:5000`**

---

### Option B: Running with MySQL (XAMPP / MySQL Server / Workbench)

1. **Start MySQL Service**:
   - Start **MySQL** via XAMPP Control Panel or MySQL Server service.
2. **Import Database (Optional)**:
   - You can import `database/library.sql` into MySQL Workbench or phpMyAdmin:
   ```bash
   mysql -u root -p < database/library.sql
   ```
   *(Alternatively, Flask will automatically create and seed the `library_db` database on first run).*
3. **Configure `.env`**:
   Verify your MySQL connection credentials in `.env`:
   ```env
   DB_TYPE=mysql
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=
   MYSQL_DB=library_db
   FALLBACK_TO_SQLITE=True
   ```
4. **Launch Application**:
   ```powershell
   python app.py
   ```

---

## 🧪 Running Automated Tests

To execute the test suite covering authentication, book CRUD, circulation desk, returns, late fines, QR codes, and reports:

```powershell
python test_app.py
```
*Expected Output: `Ran 9 tests ... OK`*

---

## ☁️ Deploying to Vercel (Production Cloud Hosting)

This project is fully configured for deployment on **[Vercel](https://vercel.com)** using its native Python Serverless Functions runtime.

### Step 1: Push Project to GitHub
```bash
git add .
git commit -m "Configure project for Vercel deployment"
git push -u origin main
```

### Step 2: Import into Vercel
1. Log in to your [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Choose your GitHub repository `Library-Management-System` and click **Import**.

### Step 3: Configure Environment Variables in Vercel
In the Vercel Project Settings → **Environment Variables**, add:

| Variable | Description | Example Value |
|---|---|---|
| `DATABASE_URL` | Cloud MySQL connection string | `mysql+pymysql://user:password@host:3306/dbname?ssl_verify_cert=true` |
| `SECRET_KEY` | Secure session cryptographic key | `your-cryptographically-secure-random-key` |
| `FLASK_DEBUG` | Production debug mode toggle | `0` |
| `FALLBACK_TO_SQLITE` | Emergency fallback in `/tmp` | `True` |

> 💡 **Recommended Free/Cloud MySQL Providers**:
> - [Aiven for MySQL](https://aiven.io/mysql)
> - [TiDB Serverless Cloud](https://tidbcloud.com) (MySQL compatible)
> - [Clever Cloud](https://www.clever-cloud.com)
> - [Amazon RDS / DigitalOcean Managed Databases](https://digitalocean.com)

### Step 4: Click Deploy
Vercel will install dependencies from `requirements.txt`, map routes via `vercel.json` to `api/index.py`, and launch your application globally on its high-speed Edge CDN.

---

## 🎨 UI/UX Features
- **Commercial Design Aesthetic**: Clean navy blue (`#1e40af`), crisp white, and light-grey theme.
- **Light & Dark Mode**: Persistent toggle in the top navbar saved in `localStorage`.
- **Responsive Layout**: Adapts gracefully across desktop monitors, laptops, tablets, and smartphones.
- **Print Ready**: Specialized `@media print` CSS for clean printing of Student ID Cards and Analytical Reports without navigation clutter.
- **Micro-Interactions**: Confirmation modals before deleting records, auto-dismissing flash alerts, and smooth card hover elevations.

