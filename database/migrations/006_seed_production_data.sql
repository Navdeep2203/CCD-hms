
-- ============================================================
-- Production-required starter data
-- Safe to run repeatedly. Does not create demo accounts,
-- demo bookings, invoices, payments or maintenance records.
-- ============================================================

-- 1. System roles
INSERT INTO roles (role_name)
VALUES
    ('ROLE_ADMIN'),
    ('ROLE_MANAGER'),
    ('ROLE_STAFF'),
    ('ROLE_CUSTOMER')
ON CONFLICT (role_name) DO NOTHING;


-- 2. Payment methods
INSERT INTO payment_methods (method_name)
VALUES
    ('Cash'),
    ('Credit Card'),
    ('UPI'),
    ('Net Banking')
ON CONFLICT (method_name) DO NOTHING;


-- 3. Departments
INSERT INTO departments (department_name)
VALUES
    ('Front Office'),
    ('Housekeeping'),
    ('Food and Beverage')
ON CONFLICT (department_name) DO NOTHING;


-- 4. Room types
INSERT INTO room_types (
    type_name,
    capacity,
    price_per_night,
    description
)
VALUES
    (
        'Standard',
        2,
        3200,
        'Compact business room with work desk'
    ),
    (
        'Deluxe',
        3,
        5200,
        'Larger room with city view'
    ),
    (
        'Suite',
        4,
        9800,
        'Premium suite with lounge space'
    )
ON CONFLICT (type_name) DO NOTHING;


-- 5. Hotel services
-- service_name does not currently have a UNIQUE constraint.
-- NOT EXISTS prevents duplicate service entries.

INSERT INTO services (service_name, price)
SELECT seed.service_name, seed.price
FROM (
    VALUES
        ('Room Dining', 850::numeric),
        ('Laundry', 450::numeric),
        ('Airport Pickup', 1800::numeric),
        ('Spa Session', 2500::numeric)
) AS seed(service_name, price)
WHERE NOT EXISTS (
    SELECT 1
    FROM services existing
    WHERE existing.service_name = seed.service_name
);
