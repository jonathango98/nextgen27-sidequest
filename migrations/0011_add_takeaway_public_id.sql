-- Takeaway.public_id and the review rules for journal.share-review (05-data-model.md section 2).
-- SQLite can't add a UNIQUE NOT NULL column or change a CHECK in place, so the table is rebuilt.
-- Nothing references takeaway, so dropping the old table is safe.

CREATE TABLE takeaway_new (
    id INTEGER PRIMARY KEY,
    -- DATA-003: the review and visibility URLs use this, never the row number (ARCH-020).
    public_id TEXT NOT NULL UNIQUE DEFAULT (lower(hex(randomblob(8)))),
    player_id INTEGER NOT NULL REFERENCES player (id),
    session_id INTEGER NOT NULL REFERENCES session (id),
    text TEXT NOT NULL CHECK (length(trim(text)) > 0),  -- word count checked on the server (GAME-034)
    visibility TEXT NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('private', 'shared_named', 'shared_anonymous')),  -- GAME-031
    review_status TEXT NOT NULL DEFAULT 'not_needed'
        CHECK (review_status IN ('not_needed', 'pending', 'approved', 'rejected', 'hidden')),
    reviewed_by INTEGER REFERENCES staff_account (id),
    reviewed_at TEXT,
    -- SAFE-007: a shared note is always reviewed. DEC-076: a rejected or hidden note made private
    -- keeps its status, so it can't be shared again.
    CHECK (
        CASE WHEN visibility = 'private'
            THEN review_status IN ('not_needed', 'rejected', 'hidden')
            ELSE review_status <> 'not_needed'
        END
    )
) STRICT;

INSERT INTO takeaway_new (id, player_id, session_id, text, visibility, review_status, reviewed_by, reviewed_at)
    SELECT id, player_id, session_id, text, visibility, review_status, reviewed_by, reviewed_at
    FROM takeaway;

DROP TABLE takeaway;
ALTER TABLE takeaway_new RENAME TO takeaway;

CREATE INDEX takeaway_player_session ON takeaway (player_id, session_id);
-- SAFE-007: the review queue and the Summary page look notes up by status.
CREATE INDEX takeaway_review_status ON takeaway (review_status);
