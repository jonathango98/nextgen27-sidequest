-- Takeaway (05-data-model.md section 2, journal.notes).
-- Timestamps are UTC ISO 8601 text (DATA-004).

-- GAME-030, DEC-072: any number of takeaways per session, so no unique pair (DATA-023 removed).
-- Points stay once per session through the ledger's unique award (DATA-027).
CREATE TABLE takeaway (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES player (id),
    session_id INTEGER NOT NULL REFERENCES session (id),
    text TEXT NOT NULL CHECK (length(trim(text)) > 0),  -- word count checked on the server (GAME-034)
    visibility TEXT NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('private', 'shared_named', 'shared_anonymous')),  -- GAME-031
    review_status TEXT NOT NULL DEFAULT 'not_needed'
        CHECK (review_status IN ('not_needed', 'pending', 'approved', 'rejected', 'hidden')),
    reviewed_by INTEGER REFERENCES staff_account (id),
    reviewed_at TEXT,
    -- SAFE-007: private notes are never reviewed, and shared ones always are.
    CHECK ((visibility = 'private') = (review_status = 'not_needed'))
) STRICT;

CREATE INDEX takeaway_player_session ON takeaway (player_id, session_id);
