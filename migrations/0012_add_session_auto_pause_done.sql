-- Session.auto_pause_done_at (05-data-model.md section 2, game-state.auto-pause).
-- 0012, not 0009: the open connections.answers PR (#79) already uses 0009.

-- GAME-107: when the server dealt with this start time, whatever the game state was, so the
-- auto-pause happens once. Null until the start time passes, and again if it moves later.
ALTER TABLE session ADD COLUMN auto_pause_done_at TEXT;
