-- AuditLog (05-data-model.md section 2, ARCH-050, ARCH-051, DATA-015).
-- Timestamps are UTC ISO 8601 text (DATA-004).
-- Rows hold IDs and short action codes only, never names, PINs, or player-written text (ARCH-051).

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    actor_type TEXT NOT NULL
        CHECK (actor_type IN ('system', 'player', 'usher', 'admin', 'screen')),
    actor_id INTEGER,
    action TEXT NOT NULL
        CHECK (length(action) BETWEEN 1 AND 64 AND action NOT GLOB '*[^a-z0-9_]*'),
    target_type TEXT
        CHECK (target_type IS NULL OR (length(target_type) BETWEEN 1 AND 64
            AND target_type NOT GLOB '*[^a-z0-9_]*')),
    target_id INTEGER,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK ((actor_type = 'system') = (actor_id IS NULL)),
    CHECK ((target_type IS NULL) = (target_id IS NULL))
) STRICT;

-- DATA-015, DATA-001: the database refuses every change to a written row.
CREATE TRIGGER audit_log_no_update
    BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log rows are never updated (DATA-015)');
END;

-- INSERT OR REPLACE removes the old row without firing delete triggers, so block reused ids.
CREATE TRIGGER audit_log_no_replace
    BEFORE INSERT ON audit_log
    WHEN EXISTS (SELECT 1 FROM audit_log WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'audit_log rows are never replaced (DATA-015)');
END;

-- The retention cleanup (SAFE-014) is the only thing allowed to delete. It drops this trigger,
-- deletes, and recreates the trigger in one transaction, so nothing else can slip in between.
CREATE TRIGGER audit_log_no_delete
    BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log rows are never deleted (DATA-015)');
END;
