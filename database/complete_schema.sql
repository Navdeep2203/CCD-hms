-- =============================================================
-- Hotel Management System - PostgreSQL Schema
-- Run this on a fresh PostgreSQL database before seed_demo.sql.
-- =============================================================

BEGIN;

DROP TABLE IF EXISTS room_maintenance CASCADE;
DROP TABLE IF EXISTS service_usage CASCADE;
DROP TABLE IF EXISTS services CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS payment_methods CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS room_types CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS managers CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS user_roles CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone_country_code VARCHAR(5),
    phone_number VARCHAR(15),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    role_id BIGSERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE user_roles (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_ur_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_ur_role FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE
);

CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    address VARCHAR(255) DEFAULT '',
    id_proof VARCHAR(100) DEFAULT '',
    nationality VARCHAR(50) DEFAULT '',
    loyalty_points INTEGER DEFAULT 0,
    CONSTRAINT fk_cust_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE departments (
    department_id BIGSERIAL PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    head_manager_id BIGINT
);

CREATE TABLE managers (
    manager_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    department_id BIGINT NOT NULL,
    reports_to_manager_id BIGINT,
    job_description VARCHAR(100),
    salary NUMERIC(10, 2),
    CONSTRAINT fk_mgr_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_mgr_dept FOREIGN KEY (department_id) REFERENCES departments(department_id),
    CONSTRAINT fk_mgr_mgr FOREIGN KEY (reports_to_manager_id) REFERENCES managers(manager_id)
);

ALTER TABLE departments
    ADD CONSTRAINT fk_dept_head
    FOREIGN KEY (head_manager_id) REFERENCES managers(manager_id);

CREATE TABLE staff (
    staff_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    department_id BIGINT NOT NULL,
    manager_id BIGINT NOT NULL,
    job_description VARCHAR(100),
    salary NUMERIC(10, 2),
    CONSTRAINT fk_staff_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_dept FOREIGN KEY (department_id) REFERENCES departments(department_id),
    CONSTRAINT fk_staff_mgr FOREIGN KEY (manager_id) REFERENCES managers(manager_id)
);

CREATE TABLE room_types (
    room_type_id BIGSERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE,
    capacity INTEGER DEFAULT 1,
    price_per_night NUMERIC(10, 2) NOT NULL,
    description VARCHAR(255)
);

CREATE TABLE rooms (
    room_id BIGSERIAL PRIMARY KEY,
    room_number INTEGER NOT NULL UNIQUE,
    room_type_id BIGINT NOT NULL,
    floor INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'AVAILABLE'
        CHECK (status IN ('AVAILABLE', 'OCCUPIED', 'MAINTENANCE', 'RESERVED')),
    CONSTRAINT fk_room_type FOREIGN KEY (room_type_id) REFERENCES room_types(room_type_id)
);

CREATE TABLE bookings (
    booking_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    room_id BIGINT NOT NULL,
    booking_date DATE DEFAULT CURRENT_DATE,
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    booking_status VARCHAR(20) DEFAULT 'PENDING'
        CHECK (booking_status IN (
            'PENDING', 'APPROVED', 'REJECTED',
            'CHECKIN_PENDING', 'CHECKED_IN',
            'CHECKOUT_PENDING', 'CHECKED_OUT',
            'CANCELLED'
        )),
    CONSTRAINT fk_book_cust FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_book_room FOREIGN KEY (room_id) REFERENCES rooms(room_id)
);

CREATE TABLE payment_methods (
    method_id BIGSERIAL PRIMARY KEY,
    method_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    booking_id BIGINT NOT NULL,
    method_id BIGINT NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    payment_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(20) DEFAULT 'COMPLETED'
        CHECK (status IN ('COMPLETED', 'PENDING', 'FAILED', 'REFUNDED')),
    CONSTRAINT fk_pay_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    CONSTRAINT fk_pay_method FOREIGN KEY (method_id) REFERENCES payment_methods(method_id)
);

CREATE TABLE invoices (
    invoice_id BIGSERIAL PRIMARY KEY,
    booking_id BIGINT NOT NULL UNIQUE,
    total_amount NUMERIC(10, 2) NOT NULL,
    tax NUMERIC(10, 2) DEFAULT 0,
    generated_date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT fk_inv_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);

CREATE TABLE services (
    service_id BIGSERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE service_usage (
    usage_id BIGSERIAL PRIMARY KEY,
    booking_id BIGINT NOT NULL,
    service_id BIGINT NOT NULL,
    quantity INTEGER DEFAULT 1,
    total_price NUMERIC(10, 2) NOT NULL,
    CONSTRAINT fk_su_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    CONSTRAINT fk_su_service FOREIGN KEY (service_id) REFERENCES services(service_id)
);

CREATE TABLE room_maintenance (
    maintenance_id BIGSERIAL PRIMARY KEY,
    room_id BIGINT NOT NULL,
    staff_id BIGINT,
    description VARCHAR(255),
    maintenance_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(20) DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED')),
    CONSTRAINT fk_maint_room FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    CONSTRAINT fk_maint_staff FOREIGN KEY (staff_id) REFERENCES staff(staff_id)
);

CREATE INDEX idx_bookings_customer_id ON bookings(customer_id);
CREATE INDEX idx_bookings_room_id ON bookings(room_id);
CREATE INDEX idx_bookings_status ON bookings(booking_status);
CREATE INDEX idx_payments_booking_id ON payments(booking_id);
CREATE INDEX idx_service_usage_booking_id ON service_usage(booking_id);

COMMIT;
