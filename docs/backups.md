# Backups and restore

How the game's data is backed up, how to bring it back, and how to delete the backups on the retention date. Rules: ARCH-053, ARCH-052, ARCH-016, SAFE-014, DEC-049, DEC-053.

Backups are Railway volume backups only. No copy is kept off Railway, and a backup restores only into the same project and environment (ARCH-053). The Railway CLI has no backup commands, so every backup step is done in the dashboard: project `nextgen27-sidequest` → environment → the app's service → **Backups** tab. The service is `nextgen27-sidequest` in production and `web` in staging and previews.

## Schedule

| Environment | Schedule | Kept for |
|---|---|---|
| production | Daily, Weekly, and Monthly | 6 days, 27 days, 89 days |
| staging | Daily | 6 days |

- Before each game day starts, press **Create backup** on production by hand.
- Manual backups are limited to half the volume size. The database is far smaller than that.

## Check the data

Read-only. It prints the integrity result and how many players there are. `<service>` is `nextgen27-sidequest` for production and `web` for staging and previews:

```bash
railway ssh -s <service> -e <environment> -- "python -c 'import os, sqlite3; c = sqlite3.connect(\"file:\" + os.environ[\"SQ_DB_PATH\"] + \"?mode=ro\", uri=True); print(c.execute(\"PRAGMA integrity_check\").fetchone()[0], c.execute(\"SELECT count(*) FROM player\").fetchone()[0], \"players\")'"
```

`ok` means the database is not damaged.

## Restore

A restore puts the game back to the moment of the backup. Everything after it is lost, and the app is down while it redeploys. Every restore also changes `SQ_SESSION_KEY`, so no login from before it still works (ARCH-034). That includes undoing a restore. During live game hours, only the developer on call decides this (ARCH-016, OPS failure playbook).

1. In the **Backups** tab, find the backup by its date stamp and press **Restore**.
2. Railway stages the change. **Don't press Deploy yet.**
3. Make a new key with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. In the same environment and service, open **Variables** and replace `SQ_SESSION_KEY` with it. Never reuse an old key, and never paste it into chat, an issue, or the repo (SAFE-030).
4. Open **Details** on the project canvas, check that it shows both the restore and the key change, and press **Deploy**. They must go out together.
5. Railway mounts a new volume named after the backup's date stamp at `/data`. The old volume stays in the project, detached, still holding the newer data.
6. Run the check above. It should print `ok`, and the player count should match the backup.
7. On a phone that was logged in before the restore, reload. It should ask to log in. Log in as a player who joined before the backup. It should work.
8. Announce that everyone, staff included, logs in again. Players need their PIN, and anyone who joined after the backup joins again. Venue Wi-Fi shares one address, so `auth.login_ip_limit_per_minute` caps how many get back in each minute. Send players back in groups.
9. Enter anything from the paper log since the backup as manual awards, with reason "paper fallback".
10. Once you're sure the restore is good, delete the old detached volume. It holds player data (SAFE-014). Railway removes it about 48 hours later, not straight away.

Tested on staging on 2026-11-02: a player who joined after the backup was gone, the integrity check printed `ok` with WAL mode on, and the app was back about 50 seconds after Deploy was pressed. The key change was added on 2026-11-21 and hasn't been tested in a Railway restore yet.

## On the retention date

The cleanup command (`app/services/retention.py`) can't reach Railway, so on the same day, in every environment:

1. Delete every backup in the **Backups** tab.
2. Delete every old volume left detached by a restore.

Tested on staging on 2026-11-02 (DEC-053, DEC-067): a single backup can be deleted in the **Backups** tab, and a detached volume can be deleted with `railway volume --environment <environment> delete --volume <name>`. Railway keeps a deleted volume for about 48 hours before it is gone, and `railway volume list` shows the "Deletes on" time.
