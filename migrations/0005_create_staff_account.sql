-- StaffAccount (05-data-model.md section 2, staff.accounts).
-- Timestamps are UTC ISO 8601 text (DATA-004). Booleans are 0 or 1.

-- ARCH-036: one personal account per usher or admin, no shared logins. Usernames ignore case,
-- so "Test-Admin" and "test-admin" can't both exist.
CREATE TABLE staff_account (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(username) BETWEEN 1 AND 64),
    password_hash TEXT NOT NULL,  -- ARCH-030: slow hash only, never the password
    -- ARCH-035: the screen role is a device mode an admin switches on, not an account (ARCH-037).
    role TEXT NOT NULL CHECK (role IN ('usher', 'admin')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),  -- switched off after the event (OPS-042)
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;
