-- Connection and ChurchMet (05-data-model.md section 2, DATA-020, DATA-021).
-- Timestamps are UTC ISO 8601 text (DATA-004). Booleans are 0 or 1.
-- Numbered 0004: 0002 is the audit log, and 0003 is left for game state (PR #49).

-- DATA-020, GAME-013, GAME-014: a pair is stored low id first, so A-B and B-A are the same row,
-- and low < high means nobody can connect with themselves.
CREATE TABLE connection (
    id INTEGER PRIMARY KEY,
    player_low_id INTEGER NOT NULL REFERENCES player (id),
    player_high_id INTEGER NOT NULL REFERENCES player (id),
    scanner_id INTEGER NOT NULL REFERENCES player (id),
    -- Set by connections.icebreaker-question. A key from icebreaker.categories (GAME-019).
    question_category TEXT
        CHECK (question_category IS NULL OR (length(question_category) BETWEEN 1 AND 64
            AND question_category NOT GLOB '*[^a-z0-9_]*')),
    is_same_church INTEGER NOT NULL CHECK (is_same_church IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK (player_low_id < player_high_id),
    CHECK (scanner_id IN (player_low_id, player_high_id)),
    UNIQUE (player_low_id, player_high_id)
) STRICT;

-- Finds every connection for a player who is the higher id of the pair.
CREATE INDEX connection_player_high ON connection (player_high_id);

-- DATA-021, GAME-011: the new church bonus is saved once per church per player.
CREATE TABLE church_met (
    id INTEGER PRIMARY KEY,  -- DATA-003
    player_id INTEGER NOT NULL REFERENCES player (id),
    church_id INTEGER NOT NULL REFERENCES church (id),
    connection_id INTEGER NOT NULL REFERENCES connection (id),
    UNIQUE (player_id, church_id)
) STRICT;
