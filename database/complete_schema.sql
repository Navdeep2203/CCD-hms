-- =============================================================
-- Hotel Management System — Complete Database Schema
-- Run this ONCE in Oracle SQL Plus on a fresh schema
-- =============================================================

-- -------------------------------------------------------------
-- 1. USERS
-- -------------------------------------------------------------
CREATE TABLE USERS (
    user_id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email            VARCHAR2(100) UNIQUE NOT NULL,
    password_hash    VARCHAR2(255) NOT NULL,
    name             VARCHAR2(100) NOT NULL,
    phone_country_code VARCHAR2(5),
    phone_number     VARCHAR2(15),
    is_active        NUMBER(1) DEFAULT 1 NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Friend's branch adds this to allow staff/manager accounts without email
ALTER TABLE USERS MODIFY (email NULL);

-- -------------------------------------------------------------
-- 2. ROLES
-- -------------------------------------------------------------
CREATE TABLE ROLES (
    role_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role_name VARCHAR2(50) NOT NULL UNIQUE
);

-- -------------------------------------------------------------
-- 3. USER_ROLES
-- -------------------------------------------------------------
CREATE TABLE USER_ROLES (
    user_id NUMBER NOT NULL,
    role_id NUMBER NOT NULL,
    CONSTRAINT pk_user_roles  PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_ur_user     FOREIGN KEY (user_id) REFERENCES USERS(user_id),
    CONSTRAINT fk_ur_role     FOREIGN KEY (role_id) REFERENCES ROLES(role_id)
);

-- -------------------------------------------------------------
-- 4. CUSTOMERS
-- -------------------------------------------------------------
CREATE TABLE CUSTOMERS (
    customer_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        NUMBER UNIQUE NOT NULL,
    address        VARCHAR2(255) DEFAULT '',
    id_proof       VARCHAR2(100) DEFAULT '',
    nationality    VARCHAR2(50)  DEFAULT '',
    loyalty_points NUMBER        DEFAULT 0,
    CONSTRAINT fk_cust_user FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);

-- -------------------------------------------------------------
-- 5. DEPARTMENTS
-- (head_manager_id FK added after MANAGERS table is created)
-- -------------------------------------------------------------
CREATE TABLE DEPARTMENTS (
    department_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name VARCHAR2(100) NOT NULL UNIQUE,
    head_manager_id NUMBER
);

-- -------------------------------------------------------------
-- 6. MANAGERS
-- -------------------------------------------------------------
CREATE TABLE MANAGERS (
    manager_id            NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id               NUMBER NOT NULL UNIQUE,
    department_id         NUMBER NOT NULL,
    reports_to_manager_id NUMBER,
    job_description       VARCHAR2(100),
    salary                NUMBER(10, 2),
    CONSTRAINT fk_mgr_user FOREIGN KEY (user_id)               REFERENCES USERS(user_id)    ON DELETE CASCADE,
    CONSTRAINT fk_mgr_dept FOREIGN KEY (department_id)         REFERENCES DEPARTMENTS(department_id),
    CONSTRAINT fk_mgr_mgr  FOREIGN KEY (reports_to_manager_id) REFERENCES MANAGERS(manager_id)
);

-- Now add the FK from DEPARTMENTS back to MANAGERS
ALTER TABLE DEPARTMENTS
    ADD CONSTRAINT fk_dept_head
    FOREIGN KEY (head_manager_id) REFERENCES MANAGERS(manager_id);

-- -------------------------------------------------------------
-- 7. STAFF
-- -------------------------------------------------------------
CREATE TABLE STAFF (
    staff_id        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         NUMBER NOT NULL UNIQUE,
    department_id   NUMBER NOT NULL,
    manager_id      NUMBER NOT NULL,
    job_description VARCHAR2(100),
    salary          NUMBER(10, 2),
    CONSTRAINT fk_staff_user FOREIGN KEY (user_id)       REFERENCES USERS(user_id)        ON DELETE CASCADE,
    CONSTRAINT fk_staff_dept FOREIGN KEY (department_id) REFERENCES DEPARTMENTS(department_id),
    CONSTRAINT fk_staff_mgr  FOREIGN KEY (manager_id)    REFERENCES MANAGERS(manager_id)
);

-- -------------------------------------------------------------
-- 8. ROOM_TYPES
-- -------------------------------------------------------------
CREATE TABLE ROOM_TYPES (
    room_type_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    type_name       VARCHAR2(50)  NOT NULL UNIQUE,
    capacity        NUMBER        DEFAULT 1,
    price_per_night NUMBER(10, 2) NOT NULL,
    description     VARCHAR2(255)
);

-- -------------------------------------------------------------
-- 9. ROOMS
-- -------------------------------------------------------------
CREATE TABLE ROOMS (
    room_id      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_number  NUMBER        NOT NULL UNIQUE,
    room_type_id NUMBER        NOT NULL,
    floor        NUMBER        DEFAULT 1,
    status       VARCHAR2(20)  DEFAULT 'AVAILABLE'
        CHECK (status IN ('AVAILABLE', 'OCCUPIED', 'MAINTENANCE', 'RESERVED')),
    CONSTRAINT fk_room_type FOREIGN KEY (room_type_id) REFERENCES ROOM_TYPES(room_type_id)
);

-- -------------------------------------------------------------
-- 10. BOOKINGS
-- -------------------------------------------------------------
CREATE TABLE BOOKINGS (
    booking_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id    NUMBER       NOT NULL,
    room_id        NUMBER       NOT NULL,
    booking_date   DATE         DEFAULT SYSDATE,
    check_in_date  DATE         NOT NULL,
    check_out_date DATE         NOT NULL,
    booking_status VARCHAR2(20) DEFAULT 'PENDING'
        CHECK (booking_status IN (
            'PENDING', 'APPROVED', 'REJECTED',
            'CHECKIN_PENDING', 'CHECKED_IN',
            'CHECKOUT_PENDING', 'CHECKED_OUT',
            'CANCELLED'
        )),
    CONSTRAINT fk_book_cust FOREIGN KEY (customer_id) REFERENCES CUSTOMERS(customer_id),
    CONSTRAINT fk_book_room FOREIGN KEY (room_id)     REFERENCES ROOMS(room_id)
);

-- -------------------------------------------------------------
-- 11. PAYMENT_METHODS
-- -------------------------------------------------------------
CREATE TABLE PAYMENT_METHODS (
    method_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    method_name VARCHAR2(50) NOT NULL UNIQUE
);

-- -------------------------------------------------------------
-- 12. PAYMENTS
-- -------------------------------------------------------------
CREATE TABLE PAYMENTS (
    payment_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    booking_id   NUMBER        NOT NULL,
    method_id    NUMBER        NOT NULL,
    amount       NUMBER(10, 2) NOT NULL,
    payment_date DATE          DEFAULT SYSDATE,
    status       VARCHAR2(20)  DEFAULT 'COMPLETED'
        CHECK (status IN ('COMPLETED', 'PENDING', 'FAILED', 'REFUNDED')),
    CONSTRAINT fk_pay_booking FOREIGN KEY (booking_id) REFERENCES BOOKINGS(booking_id),
    CONSTRAINT fk_pay_method  FOREIGN KEY (method_id)  REFERENCES PAYMENT_METHODS(method_id)
);

-- -------------------------------------------------------------
-- 13. INVOICES
-- -------------------------------------------------------------
CREATE TABLE INVOICES (
    invoice_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    booking_id     NUMBER        NOT NULL UNIQUE,
    total_amount   NUMBER(10, 2) NOT NULL,
    tax            NUMBER(10, 2) DEFAULT 0,
    generated_date DATE          DEFAULT SYSDATE,
    CONSTRAINT fk_inv_booking FOREIGN KEY (booking_id) REFERENCES BOOKINGS(booking_id)
);

-- -------------------------------------------------------------
-- 14. SERVICES
-- -------------------------------------------------------------
CREATE TABLE SERVICES (
    service_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    service_name VARCHAR2(100) NOT NULL,
    price        NUMBER(10, 2) NOT NULL
);

-- -------------------------------------------------------------
-- 15. SERVICE_USAGE
-- -------------------------------------------------------------
CREATE TABLE SERVICE_USAGE (
    usage_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    booking_id  NUMBER        NOT NULL,
    service_id  NUMBER        NOT NULL,
    quantity    NUMBER        DEFAULT 1,
    total_price NUMBER(10, 2) NOT NULL,
    CONSTRAINT fk_su_booking FOREIGN KEY (booking_id) REFERENCES BOOKINGS(booking_id),
    CONSTRAINT fk_su_service FOREIGN KEY (service_id) REFERENCES SERVICES(service_id)
);

-- -------------------------------------------------------------
-- 16. ROOM_MAINTENANCE
-- -------------------------------------------------------------
CREATE TABLE ROOM_MAINTENANCE (
    maintenance_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id          NUMBER       NOT NULL,
    staff_id         NUMBER,
    description      VARCHAR2(255),
    maintenance_date DATE         DEFAULT SYSDATE,
    status           VARCHAR2(20) DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED')),
    CONSTRAINT fk_maint_room  FOREIGN KEY (room_id)   REFERENCES ROOMS(room_id),
    CONSTRAINT fk_maint_staff FOREIGN KEY (staff_id)  REFERENCES STAFF(staff_id)
);
