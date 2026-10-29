-- GameState (05-data-model.md section 2, game-state.core).
-- Timestamps are UTC ISO 8601 text (DATA-004). Booleans are 0 or 1.

-- DATA-013: exactly one row, and state is one of the three in game.states (GAME-100).
CREATE TABLE game_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state TEXT NOT NULL CHECK (state IN ('on', 'paused', 'off')),
    wrapped_unlocked INTEGER NOT NULL DEFAULT 0 CHECK (wrapped_unlocked IN (0, 1)),  -- WRAP-002
    redemption_closed_at TEXT,  -- GAME-078
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_by INTEGER  -- staff ID. The link to the staff table comes with staff.accounts
) STRICT;

-- The start state is not in the foundation yet. "on" until Jonathan confirms (PR #49).
INSERT INTO game_state (id, state) VALUES (1, 'on');
