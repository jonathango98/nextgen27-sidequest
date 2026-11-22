-- Church.is_hidden (05-data-model.md section 2, admin.setup).

-- GAME-110, SAFE-002: an admin hides a church from the sign-up list without deleting it, so
-- players who already joined it keep their church, their points, and their login.
ALTER TABLE church ADD COLUMN is_hidden INTEGER NOT NULL DEFAULT 0 CHECK (is_hidden IN (0, 1));
