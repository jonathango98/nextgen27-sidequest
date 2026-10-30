-- PointLedger (05-data-model.md section 2, points.ledger).
-- Timestamps are UTC ISO 8601 text (DATA-004).
-- DATA-030: a player's score is the sum of amount here. Nothing else stores it.

CREATE TABLE point_ledger (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES player (id),
    amount INTEGER NOT NULL CHECK (amount <> 0),
    reason_code TEXT NOT NULL
        CHECK (length(reason_code) BETWEEN 1 AND 64 AND reason_code NOT GLOB '*[^a-z0-9_]*'),
    source_type TEXT
        CHECK (source_type IS NULL OR (length(source_type) BETWEEN 1 AND 64
            AND source_type NOT GLOB '*[^a-z0-9_]*')),
    source_id INTEGER,
    note TEXT,  -- GAME-111: required for manual awards and revocations (admin.award-revoke)
    created_by INTEGER,  -- staff ID, null for system awards. The staff link comes with staff.accounts
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK ((source_type IS NULL) = (source_id IS NULL)),
    -- GAME-004: only an admin revocation lowers a score, so system awards are positive.
    CHECK (created_by IS NOT NULL OR amount > 0),
    -- Every system award names the record that earned it, so DATA-027 below can stop double pay.
    CHECK (created_by IS NOT NULL OR source_type IS NOT NULL)
) STRICT;

-- DATA-027: the same record never pays twice, even when two requests arrive at once.
CREATE UNIQUE INDEX point_ledger_system_award_once
    ON point_ledger (player_id, reason_code, source_type, source_id)
    WHERE created_by IS NULL;
