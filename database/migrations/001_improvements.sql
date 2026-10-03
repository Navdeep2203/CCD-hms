BEGIN;

CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE bookings
ADD CONSTRAINT bookings_valid_dates
CHECK (check_out_date > check_in_date);

ALTER TABLE payments
ADD CONSTRAINT payments_positive_amount
CHECK (amount > 0);

ALTER TABLE service_usage
ADD CONSTRAINT service_usage_positive_quantity
CHECK (quantity > 0);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower
ON users(LOWER(email));

ALTER TABLE users
ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN
NOT NULL DEFAULT FALSE;

ALTER TABLE bookings
ADD COLUMN IF NOT EXISTS approved_by BIGINT;

ALTER TABLE bookings
ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR(255);

ALTER TABLE bookings
ADD CONSTRAINT fk_bookings_approved_by
FOREIGN KEY (approved_by)
REFERENCES users(user_id);

CREATE INDEX IF NOT EXISTS idx_bookings_room_checkin
ON bookings(room_id, check_in_date);

ALTER TABLE bookings
ADD CONSTRAINT no_overlapping_bookings
EXCLUDE USING gist (
    room_id WITH =,
    daterange(
        check_in_date,
        check_out_date,
        '[)'
    ) WITH &&
)
WHERE (
    booking_status IN (
        'APPROVED',
        'CHECKIN_PENDING',
        'CHECKED_IN',
        'CHECKOUT_PENDING'
    )
);

COMMIT;