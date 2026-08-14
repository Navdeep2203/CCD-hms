-- =============================================================
-- Hotel Management System - Demo seed data
-- Run after complete_schema.sql.
-- Demo password for all seeded accounts: admin123
-- =============================================================

INSERT INTO roles (role_name) VALUES ('ROLE_ADMIN');
INSERT INTO roles (role_name) VALUES ('ROLE_MANAGER');
INSERT INTO roles (role_name) VALUES ('ROLE_STAFF');
INSERT INTO roles (role_name) VALUES ('ROLE_CUSTOMER');

INSERT INTO users (email, password_hash, name, phone_country_code, phone_number)
VALUES ('admin@hotel.com', '$2a$12$SE.HqXOe6gpFtIbf5v9gRerX8wO1mgc3h4fguk8y87FKSrURRQ9iC', 'System Admin', '+91', '9000000001');

INSERT INTO users (email, password_hash, name, phone_country_code, phone_number)
VALUES ('manager@hotel.com', '$2a$12$SE.HqXOe6gpFtIbf5v9gRerX8wO1mgc3h4fguk8y87FKSrURRQ9iC', 'Aarav Mehta', '+91', '9000000002');

INSERT INTO users (email, password_hash, name, phone_country_code, phone_number)
VALUES ('staff@hotel.com', '$2a$12$SE.HqXOe6gpFtIbf5v9gRerX8wO1mgc3h4fguk8y87FKSrURRQ9iC', 'Neha Rao', '+91', '9000000003');

INSERT INTO users (email, password_hash, name, phone_country_code, phone_number)
VALUES ('customer@hotel.com', '$2a$12$SE.HqXOe6gpFtIbf5v9gRerX8wO1mgc3h4fguk8y87FKSrURRQ9iC', 'Riya Kapoor', '+91', '9000000004');

INSERT INTO user_roles (user_id, role_id)
SELECT u.user_id, r.role_id FROM users u, roles r
WHERE u.email = 'admin@hotel.com' AND r.role_name = 'ROLE_ADMIN';

INSERT INTO user_roles (user_id, role_id)
SELECT u.user_id, r.role_id FROM users u, roles r
WHERE u.email = 'manager@hotel.com' AND r.role_name = 'ROLE_MANAGER';

INSERT INTO user_roles (user_id, role_id)
SELECT u.user_id, r.role_id FROM users u, roles r
WHERE u.email = 'staff@hotel.com' AND r.role_name = 'ROLE_STAFF';

INSERT INTO user_roles (user_id, role_id)
SELECT u.user_id, r.role_id FROM users u, roles r
WHERE u.email = 'customer@hotel.com' AND r.role_name = 'ROLE_CUSTOMER';

INSERT INTO departments (department_name) VALUES ('Front Office');
INSERT INTO departments (department_name) VALUES ('Housekeeping');
INSERT INTO departments (department_name) VALUES ('Food and Beverage');

INSERT INTO managers (user_id, department_id, job_description, salary)
SELECT u.user_id, d.department_id, 'General Manager', 95000
FROM users u, departments d
WHERE u.email = 'manager@hotel.com' AND d.department_name = 'Front Office';

UPDATE departments
SET head_manager_id = (SELECT manager_id FROM managers WHERE user_id = (SELECT user_id FROM users WHERE email = 'manager@hotel.com'))
WHERE department_name = 'Front Office';

INSERT INTO staff (user_id, department_id, manager_id, job_description, salary)
SELECT u.user_id, d.department_id, m.manager_id, 'Guest Services Associate', 38000
FROM users u, departments d, managers m
WHERE u.email = 'staff@hotel.com'
  AND d.department_name = 'Front Office'
  AND m.user_id = (SELECT user_id FROM users WHERE email = 'manager@hotel.com');

INSERT INTO customers (user_id, address, id_proof, nationality, loyalty_points)
SELECT user_id, 'MG Road, Bengaluru', 'AADHAAR-0004', 'Indian', 120
FROM users
WHERE email = 'customer@hotel.com';

INSERT INTO room_types (type_name, capacity, price_per_night, description)
VALUES ('Standard', 2, 3200, 'Compact business room with work desk');
INSERT INTO room_types (type_name, capacity, price_per_night, description)
VALUES ('Deluxe', 3, 5200, 'Larger room with city view');
INSERT INTO room_types (type_name, capacity, price_per_night, description)
VALUES ('Suite', 4, 9800, 'Premium suite with lounge space');

INSERT INTO rooms (room_number, room_type_id, floor, status)
SELECT 101, room_type_id, 1, 'AVAILABLE' FROM room_types WHERE type_name = 'Standard';
INSERT INTO rooms (room_number, room_type_id, floor, status)
SELECT 102, room_type_id, 1, 'RESERVED' FROM room_types WHERE type_name = 'Deluxe';
INSERT INTO rooms (room_number, room_type_id, floor, status)
SELECT 201, room_type_id, 2, 'OCCUPIED' FROM room_types WHERE type_name = 'Suite';
INSERT INTO rooms (room_number, room_type_id, floor, status)
SELECT 202, room_type_id, 2, 'MAINTENANCE' FROM room_types WHERE type_name = 'Standard';
INSERT INTO rooms (room_number, room_type_id, floor, status)
SELECT 301, room_type_id, 3, 'AVAILABLE' FROM room_types WHERE type_name = 'Deluxe';

INSERT INTO payment_methods (method_name) VALUES ('Cash');
INSERT INTO payment_methods (method_name) VALUES ('Credit Card');
INSERT INTO payment_methods (method_name) VALUES ('UPI');
INSERT INTO payment_methods (method_name) VALUES ('Net Banking');

INSERT INTO services (service_name, price) VALUES ('Room Dining', 850);
INSERT INTO services (service_name, price) VALUES ('Laundry', 450);
INSERT INTO services (service_name, price) VALUES ('Airport Pickup', 1800);
INSERT INTO services (service_name, price) VALUES ('Spa Session', 2500);

INSERT INTO bookings (customer_id, room_id, booking_date, check_in_date, check_out_date, booking_status)
SELECT c.customer_id, r.room_id, SYSDATE - 4, SYSDATE - 1, SYSDATE + 2, 'CHECKED_IN'
FROM customers c, users u, rooms r
WHERE c.user_id = u.user_id AND u.email = 'customer@hotel.com' AND r.room_number = 201;

INSERT INTO bookings (customer_id, room_id, booking_date, check_in_date, check_out_date, booking_status)
SELECT c.customer_id, r.room_id, SYSDATE - 2, SYSDATE + 3, SYSDATE + 6, 'APPROVED'
FROM customers c, users u, rooms r
WHERE c.user_id = u.user_id AND u.email = 'customer@hotel.com' AND r.room_number = 102;

INSERT INTO service_usage (booking_id, service_id, quantity, total_price)
SELECT b.booking_id, s.service_id, 2, s.price * 2
FROM bookings b, services s
WHERE b.booking_status = 'CHECKED_IN' AND s.service_name = 'Room Dining';

INSERT INTO invoices (booking_id, total_amount, tax, generated_date)
SELECT b.booking_id, 19600, 2352, SYSDATE
FROM bookings b
WHERE b.booking_status = 'CHECKED_IN';

INSERT INTO payments (booking_id, method_id, amount, payment_date, status)
SELECT b.booking_id, pm.method_id, 8000, SYSDATE, 'COMPLETED'
FROM bookings b, payment_methods pm
WHERE b.booking_status = 'CHECKED_IN' AND pm.method_name = 'UPI';

INSERT INTO room_maintenance (room_id, staff_id, description, maintenance_date, status)
SELECT r.room_id, s.staff_id, 'Air conditioning inspection', SYSDATE, 'IN_PROGRESS'
FROM rooms r, staff s
WHERE r.room_number = 202;

COMMIT;

