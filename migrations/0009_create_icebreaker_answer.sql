-- IcebreakerAnswer (05-data-model.md section 2, connections.answers).
-- Timestamps are UTC ISO 8601 text (DATA-004).

-- GAME-015: each person types the other person's answer, so a connection has at most two rows.
-- SAFE-006: answer_text is shown only to the two players in the connection.
CREATE TABLE icebreaker_answer (
    id INTEGER PRIMARY KEY,
    connection_id INTEGER NOT NULL REFERENCES connection (id),
    about_player_id INTEGER NOT NULL REFERENCES player (id),
    typed_by_player_id INTEGER NOT NULL REFERENCES player (id),
    -- Not a game number: 200 characters fits any answer and keeps it from becoming a message (SAFE-005).
    answer_text TEXT NOT NULL CHECK (length(trim(answer_text)) BETWEEN 1 AND 200),
    -- GAME-016: connection points are given when this row is saved.
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK (about_player_id <> typed_by_player_id),
    UNIQUE (connection_id, typed_by_player_id)  -- DATA-032: one answer per person, so points pay once
) STRICT;
