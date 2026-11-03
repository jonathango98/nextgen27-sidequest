# Backups and restore

How the game's data is backed up, how to bring it back, and how to delete the backups on the retention date. Rules: ARCH-053, ARCH-052, ARCH-016, SAFE-014, DEC-049, DEC-053.

Backups are Railway volume backups only. No copy is kept off Railway, and a backup restores only into the same project and environment (ARCH-053). The Railway CLI has no backup commands, so every backup step is done in the dashboard: project `nextgen27-sidequest` → environment → `web` service → **Backups** tab.

## Schedule

| Environment | Schedule | Kept for |
|---|---|---|
| production | Daily, Weekly, and Monthly | 6 days, 27 days, 89 days |
| staging | Daily | 6 days |

- Before each game day starts, press **Create backup** on production by hand.
- Manual backups are limited to half the volume size. The database is far smaller than that.

## Check the data

Read-only. It prints the integrity result and how many players there are:

```bash
railway ssh -s web -e <environment> -- "python -c 'import sqlite3; c = sqlite3.connect(\"file:/data/side-quest.db?mode=ro\", uri=True); print(c.execute(\"PRAGMA integrity_check\").fetchone()[0], c.execute(\"SELECT count(*) FROM player\").fetchone()[0], \"players\")'"
```

`ok` means the database is not damaged.

## Restore

A restore puts the game back to the moment of the backup. Everything after it is lost, and the app is down while it redeploys. During live game hours, only the developer on call decides this (ARCH-016, OPS failure playbook).

1. In the **Backups** tab, find the backup by its date stamp and press **Restore**.
2. Railway stages the change. Open **Details** on the project canvas, check it, and press **Deploy**.
3. Railway mounts a new volume named after the backup's date stamp at `/data`. The old volume stays in the project, detached, still holding the newer data.
4. Run the check above. It should print `ok`, and the player count should match the backup.
5. Log in on a phone as a player who joined before the backup. It should work.
6. Enter anything from the paper log since the backup as manual awards, with reason "paper fallback".
7. Once you're sure the restore is good, delete the old detached volume. It holds player data (SAFE-014).

Tested on staging on 2026-11-03: a player who joined after the backup was gone, the integrity check printed `ok` with WAL mode on, and the app was back about 50 seconds after Deploy was pressed.

## On the retention date

The cleanup command (`app/services/retention.py`) can't reach Railway, so on the same day, in every environment:

1. Delete every backup in the **Backups** tab.
2. Delete every old volume left detached by a restore.

Wiping a volume deletes all of its backups. Deleting a single backup by hand has not been tried yet. Developers confirm it before Playtest 2 (DEC-053).
