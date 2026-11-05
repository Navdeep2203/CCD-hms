INSERT INTO roles (role_name)
VALUES
    ('ROLE_ADMIN'),
    ('ROLE_MANAGER'),
    ('ROLE_STAFF'),
    ('ROLE_CUSTOMER')
ON CONFLICT (role_name) DO NOTHING;