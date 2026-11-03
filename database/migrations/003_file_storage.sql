
-- Add Supabase Storage object-key references.
-- Existing records remain valid because all columns are nullable.

ALTER TABLE room_types
ADD COLUMN IF NOT EXISTS image_key VARCHAR(255);

ALTER TABLE customers
ADD COLUMN IF NOT EXISTS id_proof_key VARCHAR(255);

ALTER TABLE room_maintenance
ADD COLUMN IF NOT EXISTS photo_key VARCHAR(255);

ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS pdf_key VARCHAR(255);
