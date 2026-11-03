-- Session and CheckIn (05-data-model.md section 2, checkin.sessions).
-- Timestamps are UTC ISO 8601 text (DATA-004).

-- DATA-014: a title, an optional start time, and check-in minutes. No room names or places (SAFE-037).
CREATE TABLE session (
    id INTEGER PRIMARY KEY,
    public_id TEXT NOT NULL UNIQUE,  -- DATA-003: used in URLs and the check-in QR (ARCH-020)
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    ended_at TEXT,  -- GAME-026: set by End session. Takeaways open then (GAME-036)
    checkin_closed_at TEXT,  -- GAME-024, GAME-026
    checkin_opened_at TEXT,  -- GAME-027: Open check-in comes with checkin.window
    starts_at TEXT,  -- admin only, except the hall countdown (DATA-014, GAME-028)
    checkin_open_minutes INTEGER CHECK (checkin_open_minutes IS NULL OR checkin_open_minutes > 0),
    -- GAME-021: check-in opens this many minutes before the start, so a start time needs them.
    CHECK (starts_at IS NULL OR checkin_open_minutes IS NOT NULL)
) STRICT;

-- Check-ins are saved by checkin.window. The table comes now with its two uniques (DATA-022).
CREATE TABLE check_in (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES player (id),
    session_id INTEGER NOT NULL REFERENCES session (id),
    scan_order INTEGER NOT NULL CHECK (scan_order > 0),  -- GAME-025: 1 for the first check-in
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (player_id, session_id),  -- GAME-023: once per session
    UNIQUE (session_id, scan_order)
) STRICT;
