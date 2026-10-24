-- Church and Player (05-data-model.md section 2, issue #25).
-- Timestamps are UTC ISO 8601 text (DATA-004). Booleans are 0 or 1.

CREATE TABLE church (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    region TEXT  -- DATA-010 OPEN
) STRICT;

-- DATA-011: no other personal fields. DATA-002: no email or phone.
CREATE TABLE player (
    id INTEGER PRIMARY KEY,
    public_id TEXT NOT NULL UNIQUE,  -- ARCH-020, DATA-003
    first_name TEXT NOT NULL CHECK (first_name <> '' AND first_name = trim(first_name)),
    last_name TEXT NOT NULL CHECK (last_name <> '' AND last_name = trim(last_name)),
    church_id INTEGER NOT NULL REFERENCES church (id),
    is_under_18 INTEGER NOT NULL CHECK (is_under_18 IN (0, 1)),
    pin_hash TEXT NOT NULL,  -- SAFE-021, ARCH-030
    failed_pin_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_pin_attempts >= 0),
    locked_at TEXT,  -- SAFE-022
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;

-- DATA-016, ARCH-033: one full name per church, ignoring case.
CREATE UNIQUE INDEX player_church_full_name
    ON player (church_id, first_name COLLATE NOCASE, last_name COLLATE NOCASE);
