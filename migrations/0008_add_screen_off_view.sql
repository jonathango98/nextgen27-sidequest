-- GameState.screen_off_view (05-data-model.md section 2, screen.main).
-- 0008, not 0007: the open check-in PR (#76) already uses 0007.

-- UI-044: what the main screen shows while the game is off. Starts as the offline message.
ALTER TABLE game_state ADD COLUMN screen_off_view TEXT NOT NULL DEFAULT 'offline'
    CHECK (screen_off_view IN ('offline', 'recap'));
