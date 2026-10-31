-- ========================================================
-- PROFESSIONAL LIBRARY MANAGEMENT SYSTEM DATABASE SCRIPT
-- Dialect: MySQL 5.7+ / MySQL 8.0+ / MariaDB
-- Character Set: utf8mb4 / utf8mb4_unicode_ci
-- ========================================================

CREATE DATABASE IF NOT EXISTS `library_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `library_db`;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `book_locations`;
DROP TABLE IF EXISTS `shelves`;
DROP TABLE IF EXISTS `racks`;
DROP TABLE IF EXISTS `rooms`;
DROP TABLE IF EXISTS `sections`;
DROP TABLE IF EXISTS `floors`;
DROP TABLE IF EXISTS `activity_logs`;
DROP TABLE IF EXISTS `reviews`;
DROP TABLE IF EXISTS `ebooks`;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `fines`;
DROP TABLE IF EXISTS `reservations`;
DROP TABLE IF EXISTS `book_returns`;
DROP TABLE IF EXISTS `book_issues`;
DROP TABLE IF EXISTS `books`;
DROP TABLE IF EXISTS `categories`;
DROP TABLE IF EXISTS `students`;
DROP TABLE IF EXISTS `librarians`;
DROP TABLE IF EXISTS `admins`;
DROP TABLE IF EXISTS `settings`;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. ADMIN TABLE
CREATE TABLE `admins` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(64) NOT NULL UNIQUE,
    `name` VARCHAR(120) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `avatar` VARCHAR(255) DEFAULT 'default_avatar.png',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_admin_username` (`username`),
    INDEX `idx_admin_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. LIBRARIANS TABLE
CREATE TABLE `librarians` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `librarian_id` VARCHAR(32) NOT NULL UNIQUE,
    `name` VARCHAR(120) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `phone` VARCHAR(20) DEFAULT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `permissions` TEXT,
    `status` VARCHAR(20) DEFAULT 'active',
    `avatar` VARCHAR(255) DEFAULT 'default_avatar.png',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_lib_code` (`librarian_id`),
    INDEX `idx_lib_email` (`email`),
    INDEX `idx_lib_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. STUDENTS TABLE
CREATE TABLE `students` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` VARCHAR(32) NOT NULL UNIQUE,
    `name` VARCHAR(120) NOT NULL,
    `department` VARCHAR(100) NOT NULL,
    `academic_year` VARCHAR(50) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `phone` VARCHAR(20) NOT NULL,
    `address` TEXT DEFAULT NULL,
    `avatar` VARCHAR(255) DEFAULT 'default_avatar.png',
    `password_hash` VARCHAR(255) NOT NULL,
    `status` VARCHAR(20) DEFAULT 'active',
    `qr_code_image` VARCHAR(255) DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_stu_id` (`student_id`),
    INDEX `idx_stu_email` (`email`),
    INDEX `idx_stu_dept` (`department`),
    INDEX `idx_stu_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. CATEGORIES TABLE
CREATE TABLE `categories` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `description` TEXT DEFAULT NULL,
    `icon` VARCHAR(50) DEFAULT 'bi-bookmark',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_cat_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. BOOKS TABLE
CREATE TABLE `books` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `isbn` VARCHAR(32) NOT NULL UNIQUE,
    `title` VARCHAR(255) NOT NULL,
    `author` VARCHAR(255) NOT NULL,
    `publisher` VARCHAR(255) DEFAULT NULL,
    `category_id` INT DEFAULT NULL,
    `publication_year` INT DEFAULT NULL,
    `total_copies` INT NOT NULL DEFAULT 1,
    `available_copies` INT NOT NULL DEFAULT 1,
    `shelf_location` VARCHAR(64) DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `cover_image` VARCHAR(255) DEFAULT 'default_book_cover.png',
    `qr_code_image` VARCHAR(255) DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_book_isbn` (`isbn`),
    INDEX `idx_book_title` (`title`),
    INDEX `idx_book_author` (`author`),
    INDEX `idx_book_cat` (`category_id`),
    CONSTRAINT `fk_books_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. BOOK ISSUES TABLE
CREATE TABLE `book_issues` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `issue_code` VARCHAR(32) NOT NULL UNIQUE,
    `book_id` INT NOT NULL,
    `student_id` INT NOT NULL,
    `issued_by_type` VARCHAR(20) DEFAULT 'admin',
    `issued_by_id` INT DEFAULT 1,
    `issue_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `due_date` DATETIME NOT NULL,
    `return_date` DATETIME DEFAULT NULL,
    `status` VARCHAR(20) DEFAULT 'issued',
    `notes` TEXT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_issue_code` (`issue_code`),
    INDEX `idx_issue_book` (`book_id`),
    INDEX `idx_issue_student` (`student_id`),
    INDEX `idx_issue_status` (`status`),
    INDEX `idx_issue_due` (`due_date`),
    CONSTRAINT `fk_issues_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_issues_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. BOOK RETURNS TABLE
CREATE TABLE `book_returns` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `issue_id` INT NOT NULL UNIQUE,
    `book_id` INT NOT NULL,
    `student_id` INT NOT NULL,
    `received_by_type` VARCHAR(20) DEFAULT 'admin',
    `received_by_id` INT DEFAULT 1,
    `return_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `overdue_days` INT DEFAULT 0,
    `fine_amount` DECIMAL(10,2) DEFAULT 0.00,
    `condition_notes` TEXT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_ret_issue` (`issue_id`),
    INDEX `idx_ret_book` (`book_id`),
    INDEX `idx_ret_student` (`student_id`),
    CONSTRAINT `fk_returns_issue` FOREIGN KEY (`issue_id`) REFERENCES `book_issues` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_returns_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_returns_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. RESERVATIONS TABLE
CREATE TABLE `reservations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `reservation_code` VARCHAR(32) NOT NULL UNIQUE,
    `book_id` INT NOT NULL,
    `student_id` INT NOT NULL,
    `reservation_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `status` VARCHAR(20) DEFAULT 'pending',
    `queue_position` INT DEFAULT 1,
    `notified_at` DATETIME DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_res_code` (`reservation_code`),
    INDEX `idx_res_book` (`book_id`),
    INDEX `idx_res_student` (`student_id`),
    INDEX `idx_res_status` (`status`),
    CONSTRAINT `fk_res_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_res_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. FINES TABLE
CREATE TABLE `fines` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `issue_id` INT NOT NULL,
    `student_id` INT NOT NULL,
    `amount` DECIMAL(10,2) NOT NULL,
    `overdue_days` INT DEFAULT 0,
    `status` VARCHAR(20) DEFAULT 'pending',
    `payment_date` DATETIME DEFAULT NULL,
    `payment_method` VARCHAR(50) DEFAULT NULL,
    `transaction_id` VARCHAR(100) DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_fines_issue` (`issue_id`),
    INDEX `idx_fines_student` (`student_id`),
    INDEX `idx_fines_status` (`status`),
    CONSTRAINT `fk_fines_issue` FOREIGN KEY (`issue_id`) REFERENCES `book_issues` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_fines_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. NOTIFICATIONS TABLE
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `recipient_type` VARCHAR(20) NOT NULL,
    `recipient_id` INT DEFAULT NULL,
    `title` VARCHAR(255) NOT NULL,
    `message` TEXT NOT NULL,
    `type` VARCHAR(20) DEFAULT 'info',
    `is_read` BOOLEAN DEFAULT FALSE,
    `link` VARCHAR(255) DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_notif_recipient` (`recipient_type`, `recipient_id`),
    INDEX `idx_notif_read` (`is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. EBOOKS TABLE
CREATE TABLE `ebooks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(255) NOT NULL,
    `author` VARCHAR(255) NOT NULL,
    `category_id` INT DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `cover_image` VARCHAR(255) DEFAULT 'default_ebook_cover.png',
    `file_size_mb` DECIMAL(8,2) DEFAULT 0.00,
    `downloads_count` INT DEFAULT 0,
    `views_count` INT DEFAULT 0,
    `is_downloadable` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_ebook_title` (`title`),
    INDEX `idx_ebook_author` (`author`),
    INDEX `idx_ebook_cat` (`category_id`),
    CONSTRAINT `fk_ebooks_cat` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. REVIEWS TABLE
CREATE TABLE `reviews` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `book_id` INT NOT NULL,
    `student_id` INT NOT NULL,
    `rating` INT NOT NULL CHECK (`rating` BETWEEN 1 AND 5),
    `review_text` TEXT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_rev_book` (`book_id`),
    INDEX `idx_rev_student` (`student_id`),
    CONSTRAINT `fk_rev_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_rev_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. ACTIVITY LOGS TABLE
CREATE TABLE `activity_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_type` VARCHAR(20) NOT NULL,
    `user_id` INT DEFAULT NULL,
    `user_name` VARCHAR(120) DEFAULT NULL,
    `action` VARCHAR(120) NOT NULL,
    `details` TEXT DEFAULT NULL,
    `ip_address` VARCHAR(45) DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_log_user` (`user_type`, `user_id`),
    INDEX `idx_log_action` (`action`),
    INDEX `idx_log_time` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. SETTINGS TABLE
CREATE TABLE `settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(64) NOT NULL UNIQUE,
    `value` TEXT NOT NULL,
    `description` VARCHAR(255) DEFAULT NULL,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_setting_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 15. FLOORS TABLE (SMART SHELF TRACKING)
CREATE TABLE `floors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `floor_number` INT NOT NULL UNIQUE,
    `name` VARCHAR(100) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_floor_num` (`floor_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 16. SECTIONS TABLE
CREATE TABLE `sections` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `code` VARCHAR(32) NOT NULL UNIQUE,
    `floor_id` INT NOT NULL,
    `description` TEXT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_section_code` (`code`),
    INDEX `idx_section_floor` (`floor_id`),
    CONSTRAINT `fk_sections_floor` FOREIGN KEY (`floor_id`) REFERENCES `floors` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 17. ROOMS TABLE
CREATE TABLE `rooms` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `room_number` VARCHAR(50) NOT NULL,
    `name` VARCHAR(100) DEFAULT NULL,
    `floor_id` INT NOT NULL,
    `section_id` INT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_room_number` (`room_number`),
    INDEX `idx_room_floor` (`floor_id`),
    INDEX `idx_room_section` (`section_id`),
    CONSTRAINT `fk_rooms_floor` FOREIGN KEY (`floor_id`) REFERENCES `floors` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_rooms_section` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 18. RACKS TABLE
CREATE TABLE `racks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `rack_number` VARCHAR(50) NOT NULL,
    `room_id` INT NOT NULL,
    `section_id` INT DEFAULT NULL,
    `description` VARCHAR(255) DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_rack_number` (`rack_number`),
    INDEX `idx_rack_room` (`room_id`),
    INDEX `idx_rack_section` (`section_id`),
    CONSTRAINT `fk_racks_room` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_racks_section` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 19. SHELVES TABLE
CREATE TABLE `shelves` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `shelf_number` VARCHAR(50) NOT NULL,
    `rack_id` INT NOT NULL,
    `capacity` INT NOT NULL DEFAULT 25,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_shelf_number` (`shelf_number`),
    INDEX `idx_shelf_rack` (`rack_id`),
    CONSTRAINT `fk_shelves_rack` FOREIGN KEY (`rack_id`) REFERENCES `racks` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 20. BOOK LOCATIONS TABLE
CREATE TABLE `book_locations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `book_id` INT NOT NULL,
    `shelf_id` INT DEFAULT NULL,
    `copy_number` INT NOT NULL DEFAULT 1,
    `barcode` VARCHAR(64) NOT NULL UNIQUE,
    `position_code` VARCHAR(32) DEFAULT NULL,
    `status` VARCHAR(20) DEFAULT 'on_shelf',
    `last_confirmed_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `notes` TEXT DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_bloc_book` (`book_id`),
    INDEX `idx_bloc_shelf` (`shelf_id`),
    INDEX `idx_bloc_barcode` (`barcode`),
    INDEX `idx_bloc_status` (`status`),
    CONSTRAINT `fk_bloc_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_bloc_shelf` FOREIGN KEY (`shelf_id`) REFERENCES `shelves` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ========================================================
-- INITIAL SEED DATA
-- Default Passwords:
-- Admin: admin123
-- Librarian: librarian123
-- Students: student123
-- (Hashed using Werkzeug scrypt / pbkdf2)
-- ========================================================

-- Settings
INSERT INTO `settings` (`key`, `value`, `description`) VALUES
('library_name', 'Apex Central Digital Library', 'Official institution library title'),
('contact_email', 'library@apex.edu', 'Helpdesk contact email'),
('phone_number', '+1 (555) 019-2834', 'Circulation desk telephone'),
('address', '100 University Avenue, Tech Campus, Building B', 'Physical campus address'),
('currency_symbol', '$', 'Default monetary currency symbol'),
('fine_per_day', '1.00', 'Late return fine amount charged per day'),
('issue_duration_days', '14', 'Default loan period in days'),
('max_books_per_student', '3', 'Maximum simultaneous books allowed per student'),
('reservation_hold_hours', '48', 'Hours to hold reserved book before release');

-- Admin Account (Password: admin123)
-- Hash generated by werkzeug.security: scrypt:32768:8:1$uH34G6Y...
INSERT INTO `admins` (`username`, `name`, `email`, `password_hash`) VALUES
('admin', 'Dr. Alistair Vance', 'admin@apex.edu', 'scrypt:32768:8:1$mFhN5Z2n2G3X9kP1$568df56ec2f20436d6be47225c50c5ff4f941f1737be543da65a12154d89617d9fc8774775d71c1b3f9fc3aa5d2c2576b5dcf66cf9b50db15d9bece6ad59f939');

-- Librarians (Password: librarian123)
INSERT INTO `librarians` (`librarian_id`, `name`, `email`, `phone`, `password_hash`, `permissions`, `status`) VALUES
('LIB-001', 'Eleanor Rigby', 'librarian@apex.edu', '+1-555-0101', 'scrypt:32768:8:1$mFhN5Z2n2G3X9kP1$568df56ec2f20436d6be47225c50c5ff4f941f1737be543da65a12154d89617d9fc8774775d71c1b3f9fc3aa5d2c2576b5dcf66cf9b50db15d9bece6ad59f939', 'books,issues,returns,reservations,students,fines,reports', 'active'),
('LIB-002', 'Marcus Holloway', 'marcus.h@apex.edu', '+1-555-0102', 'scrypt:32768:8:1$mFhN5Z2n2G3X9kP1$568df56ec2f20436d6be47225c50c5ff4f941f1737be543da65a12154d89617d9fc8774775d71c1b3f9fc3aa5d2c2576b5dcf66cf9b50db15d9bece6ad59f939', 'books,issues,returns,reservations', 'active');

-- Students (Password: student123)
INSERT INTO `students` (`student_id`, `name`, `department`, `academic_year`, `email`, `phone`, `address`, `password_hash`, `status`) VALUES
('STU-2026-001', 'Alexander Hayes', 'Computer Science & Engineering', 'Final Year (2025-2026)', 'student@apex.edu', '+1-555-0201', 'Room 304, Redwood Hall, Campus', 'scrypt:32768:8:1$mFhN5Z2n2G3X9kP1$568df56ec2f20436d6be47225c50c5ff4f941f1737be543da65a12154d89617d9fc8774775d71c1b3f9fc3aa5d2c2576b5dcf66cf9b50db15d9bece6ad59f939', 'active'),
('STU-2026-002', 'Sophia Chen', 'Data Science & AI', '3rd Year', 'sophia.c@apex.edu', '+1-555-0202', '742 Evergreen Terrace, North District', 'scrypt:32768:8:1$mFhN5Z2n2G3X9kP1$568df56ec2f20436d6be47225c50c5ff4f941f1737be543da65a12154d89617d9fc8774775d71c1b3f9fc3aa5d2c2576b5dcf66cf9b50db15d9bece6ad59f939', 'active'),
('STU-2026-003', 'Liam O\'Connor', 'Mechanical Engineering', '2nd Year', 'liam.oc@apex.edu', '+1-555-0203', 'Flat 12, Parkside Apartments', 'scrypt:32768:8:1$mFhN5Z2n2G3X9kP1$568df56ec2f20436d6be47225c50c5ff4f941f1737be543da65a12154d89617d9fc8774775d71c1b3f9fc3aa5d2c2576b5dcf66cf9b50db15d9bece6ad59f939', 'active'),
('STU-2026-004', 'Emily Rodriguez', 'Electrical & Electronics', 'Final Year (2025-2026)', 'emily.r@apex.edu', '+1-555-0204', 'Room 112, Magnolia Residence', 'scrypt:32768:8:1$mFhN5Z2n2G3X9kP1$568df56ec2f20436d6be47225c50c5ff4f941f1737be543da65a12154d89617d9fc8774775d71c1b3f9fc3aa5d2c2576b5dcf66cf9b50db15d9bece6ad59f939', 'active');

-- Categories
INSERT INTO `categories` (`id`, `name`, `description`, `icon`) VALUES
(1, 'Computer Science & Software', 'Algorithms, architecture, data structures, and programming paradigms.', 'bi-laptop'),
(2, 'Artificial Intelligence & ML', 'Machine learning, neural networks, deep learning, and intelligent agents.', 'bi-cpu'),
(3, 'Database & Systems Design', 'Relational models, distributed data architectures, and SQL engines.', 'bi-database'),
(4, 'Mathematics & Statistics', 'Calculus, linear algebra, discrete math, and probability.', 'bi-calculator'),
(5, 'Electronics & Robotics', 'Embedded systems, microcontrollers, circuits, and sensors.', 'bi-motherboard'),
(6, 'Business & Management', 'Technology entrepreneurship, project leadership, and organizational psychology.', 'bi-briefcase');

-- Books
INSERT INTO `books` (`id`, `isbn`, `title`, `author`, `publisher`, `category_id`, `publication_year`, `total_copies`, `available_copies`, `shelf_location`, `description`) VALUES
(1, '978-0132350884', 'Clean Code: A Handbook of Agile Software Craftsmanship', 'Robert C. Martin', 'Prentice Hall', 1, 2008, 5, 4, 'Shelf CS-01', 'Even bad code can function. But if code isn\'t clean, it can bring a development organization to its knees.'),
(2, '978-0262033848', 'Introduction to Algorithms (CLRS)', 'Thomas H. Cormen et al.', 'MIT Press', 1, 2009, 8, 6, 'Shelf CS-02', 'Comprehensive textbook covering depth and rigor across algorithm design, dynamic programming, graph theory, and complexity analysis.'),
(3, '978-0134685991', 'Effective Java (3rd Edition)', 'Joshua Bloch', 'Addison-Wesley Professional', 1, 2018, 4, 3, 'Shelf CS-03', 'Definitive guide to Java best practices, design patterns, and modern idiomatic programming.'),
(4, '978-0262035613', 'Deep Learning', 'Ian Goodfellow, Yoshua Bengio, Aaron Courville', 'MIT Press', 2, 2016, 6, 5, 'Shelf AI-01', 'An introduction to mathematical and conceptual foundations of deep learning architectures and neural optimization.'),
(5, '978-1449369415', 'Designing Data-Intensive Applications', 'Martin Kleppmann', 'O\'Reilly Media', 3, 2017, 7, 5, 'Shelf DB-01', 'The definitive guide to the architecture of reliable, scalable, and maintainable distributed data systems.'),
(6, '978-0131103627', 'The C Programming Language (2nd Edition)', 'Brian W. Kernighan, Dennis M. Ritchie', 'Prentice Hall', 1, 1988, 5, 4, 'Shelf CS-04', 'The classic authoritative guide to C programming language by its creators.'),
(7, '978-1491957660', 'Hands-On Machine Learning with Scikit-Learn and TensorFlow', 'Aurélien Géron', 'O\'Reilly Media', 2, 2019, 5, 4, 'Shelf AI-02', 'Through a series of recent breakthroughs, deep learning has boosted the entire field of machine learning.'),
(8, '978-0321125217', 'Domain-Driven Design: Tackling Complexity in Software', 'Eric Evans', 'Addison-Wesley', 1, 2003, 3, 2, 'Shelf CS-05', 'Systematic approach to software design connecting an implementation to an evolving model.');

-- Sample Book Issues
INSERT INTO `book_issues` (`id`, `issue_code`, `book_id`, `student_id`, `issued_by_type`, `issued_by_id`, `issue_date`, `due_date`, `status`, `notes`) VALUES
(1, 'ISS-2026-0001', 1, 1, 'admin', 1, DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_ADD(NOW(), INTERVAL 9 DAY), 'issued', 'Standard 14-day checkout'),
(2, 'ISS-2026-0002', 5, 2, 'librarian', 1, DATE_SUB(NOW(), INTERVAL 20 DAY), DATE_SUB(NOW(), INTERVAL 6 DAY), 'overdue', 'System marked overdue alert'),
(3, 'ISS-2026-0003', 2, 3, 'librarian', 1, DATE_SUB(NOW(), INTERVAL 16 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY), 'returned', 'Returned with 2 days late fee');

-- Sample Book Return
INSERT INTO `book_returns` (`id`, `issue_id`, `book_id`, `student_id`, `received_by_type`, `received_by_id`, `return_date`, `overdue_days`, `fine_amount`, `condition_notes`) VALUES
(1, 3, 2, 3, 'librarian', 1, NOW(), 2, 2.00, 'Returned in excellent condition');

-- Sample Fine
INSERT INTO `fines` (`id`, `issue_id`, `student_id`, `amount`, `overdue_days`, `status`, `payment_date`, `payment_method`, `transaction_id`, `notes`) VALUES
(1, 3, 3, 2.00, 2, 'paid', NOW(), 'Cash', 'RCPT-10042', 'Late return 2 days @ $1.00/day. Paid at circulation counter.');

-- Sample Reservation
INSERT INTO `reservations` (`id`, `reservation_code`, `book_id`, `student_id`, `reservation_date`, `status`, `queue_position`) VALUES
(1, 'RES-2026-0001', 8, 1, DATE_SUB(NOW(), INTERVAL 1 DAY), 'pending', 1);

-- Sample Reviews
INSERT INTO `reviews` (`book_id`, `student_id`, `rating`, `review_text`, `created_at`) VALUES
(1, 1, 5, 'A transformative read for any aspiring software developer. Completely changed how I write methods and structure classes.', NOW()),
(5, 2, 5, 'Hands down the best technology book ever written on distributed systems and database internals!', NOW());

-- Sample Activity Logs
INSERT INTO `activity_logs` (`user_type`, `user_id`, `user_name`, `action`, `details`, `ip_address`) VALUES
('system', NULL, 'Database Seed', 'System Initialization', 'Seeded initial database records with admin, librarian, and catalog.', '127.0.0.1');

-- Floors
INSERT INTO `floors` (`id`, `floor_number`, `name`, `description`) VALUES
(1, 0, 'Ground Floor', 'Main Circulation, Reference Desk, Computer Science & High-Density Stacks'),
(2, 1, 'First Floor', 'Mathematics, Natural Sciences, Quiet Study Suites & Research Carrels'),
(3, 2, 'Second Floor', 'Humanities, Economics, Management, Digital Media Lab & Archives');

-- Sections
INSERT INTO `sections` (`id`, `name`, `code`, `floor_id`, `description`) VALUES
(1, 'Computer Science', 'SEC-CS', 1, 'Computing paradigms, software architecture, algorithmics & networks'),
(2, 'Database & Systems', 'SEC-DB', 1, 'Distributed systems, relational & NoSQL database storage engines'),
(3, 'Artificial Intelligence', 'SEC-AI', 1, 'Machine learning, robotics, neural models & computer vision'),
(4, 'Mathematics & Statistics', 'SEC-MATH', 2, 'Applied statistics, pure calculus, probability & optimization'),
(5, 'Business & Management', 'SEC-BUS', 3, 'Technology leadership, organizational strategy & economics');

-- Rooms
INSERT INTO `rooms` (`id`, `room_number`, `name`, `floor_id`, `section_id`) VALUES
(1, 'Room 101', 'Main Computing Archives & Open Stacks', 1, 1),
(2, 'Room 102', 'Systems & High-Performance Data Wing', 1, 2),
(3, 'Room 201', 'Quantitative & Mathematics Library', 2, 4),
(4, 'Room 301', 'Management, Innovation & Reading Hall', 3, 5);

-- Racks
INSERT INTO `racks` (`id`, `rack_number`, `room_id`, `section_id`, `description`) VALUES
(1, 'Rack R05', 1, 1, 'Computer Science Software Engineering Stacks'),
(2, 'Rack R01', 1, 1, 'Computer Science Theory & Algorithms'),
(3, 'Rack R02', 2, 2, 'Database Systems & Architecture Stacks'),
(4, 'Rack R03', 1, 3, 'Artificial Intelligence & Machine Learning');

-- Shelves
INSERT INTO `shelves` (`id`, `shelf_number`, `rack_id`, `capacity`) VALUES
(1, 'Shelf S01', 1, 30),
(2, 'Shelf S02', 1, 30),
(3, 'Shelf S03', 1, 25),
(4, 'Shelf S04', 1, 25),
(5, 'Shelf S01', 2, 35),
(6, 'Shelf S02', 2, 35),
(7, 'Shelf S01', 3, 25),
(8, 'Shelf S02', 3, 25),
(9, 'Shelf S01', 4, 30),
(10, 'Shelf S02', 4, 30);

-- Book Physical Copy Locations
-- Clean Code -> Ground Floor → Computer Science → Room 101 → Rack R05 → Shelf S03 → Position B12
INSERT INTO `book_locations` (`book_id`, `shelf_id`, `copy_number`, `barcode`, `position_code`, `status`, `notes`) VALUES
(1, 3, 1, 'BC-BK1-C1', 'B12', 'issued', 'Assigned to primary curriculum shelf'),
(1, 3, 2, 'BC-BK1-C2', 'B13', 'on_shelf', 'Copy 2 on shelf'),
(1, 3, 3, 'BC-BK1-C3', 'B14', 'on_shelf', 'Copy 3 on shelf'),
(1, 3, 4, 'BC-BK1-C4', 'B15', 'on_shelf', 'Copy 4 on shelf'),
(1, 3, 5, 'BC-BK1-C5', 'B16', 'on_shelf', 'Copy 5 on shelf'),
(2, 5, 1, 'BC-BK2-C1', 'A01', 'on_shelf', 'Primary reference copy'),
(3, 1, 1, 'BC-BK3-C1', 'C04', 'on_shelf', 'General circulation'),
(4, 9, 1, 'BC-BK4-C1', 'D08', 'on_shelf', 'AI research stacks'),
(5, 7, 1, 'BC-BK5-C1', 'E02', 'on_shelf', 'Data engineering collection'),
(6, 2, 1, 'BC-BK6-C1', 'A10', 'on_shelf', 'Classic C programming'),
(7, 10, 1, 'BC-BK7-C1', 'D14', 'on_shelf', 'ML applied collection'),
(8, 4, 1, 'BC-BK8-C1', 'B05', 'on_shelf', 'Software architecture');

