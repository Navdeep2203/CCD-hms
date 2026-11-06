
INSERT INTO payment_methods (method_name)
VALUES
    ('Cash'),
    ('Credit Card'),
    ('UPI'),
    ('Net Banking')
ON CONFLICT (method_name) DO NOTHING;
