# 05 Data Model

- Status: PROPOSED (developers confirm at kickoff; constraints marked LOCKED are required whatever the final schema looks like)
- Owner: Jonathan (@jonathango98)
- Version: 1.3.0
- Last updated: 2026-10-26

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file lists the tables, their fields, and the database constraints that enforce game rules. The database is SQLite (ARCH-001). Table and field names are PROPOSED. Any schema change needs an issue and safety review when it touches player data (SAFE-016). Stop and ask before changing the schema (AI-050).

## 1. Rules for the whole schema

- **DATA-001** [LOCKED] Rules that can be enforced by the database are enforced by the database (unique constraints, foreign keys, checks), not only by code. If two phones send the same scan at the same moment, the database refuses the second one.
- **DATA-002** [LOCKED] No table has a column for email or phone number (SAFE-003).
- **DATA-003** [PROPOSED] Every table has an integer primary key `id` for internal use. Anything shown in a QR code or URL uses a separate random `public_id` (ARCH-020).
- **DATA-004** [LOCKED] All timestamps are stored in UTC (ARCH-015).
- **DATA-005** [LOCKED] Foreign keys are switched on in SQLite for every connection.

## 2. Entities

### Church

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `name` | text | Unique. Loaded by an admin before the event (SAFE-002) |
| `region` | text, nullable | Unused. Regions were dropped (DATA-010) |

### Player

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `public_id` | text | Unique, random (ARCH-020) |
| `first_name` | text | Shown to other players |
| `last_name` | text | Admins and ushers only (SAFE-004) |
| `church_id` | integer | Foreign key to Church |
| `is_under_18` | boolean | Admins only (SAFE-020) |
| `pin_hash` | text | Slow hash only (SAFE-021, ARCH-030) |
| `failed_pin_attempts` | integer | Reset to 0 after a correct PIN |
| `locked_at` | timestamp, nullable | Set after 5 wrong tries (SAFE-022) |
| `created_at` | timestamp | Sign-up time |

- **DATA-011** [LOCKED] Player has no other personal fields. Adding one needs a Foundation Change Request (SAFE-002).
- **DATA-012** [PROPOSED] Players cannot change their own church after sign-up. Only an admin can fix a wrong church, and that writes an audit row.
- **DATA-016** [LOCKED] Player: `UNIQUE (church_id, first_name COLLATE NOCASE, last_name COLLATE NOCASE)`. Names have spaces trimmed from both ends before saving. One full name per church (ARCH-033, DEC-033).

### StaffAccount (ushers and admins)

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `username` | text | Unique. Not a real name in seed data |
| `password_hash` | text | Slow hash (ARCH-036) |
| `role` | text | `usher` or `admin` |
| `is_active` | boolean | Admins switch accounts off after the event |

### GameState

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Always 1. Exactly one row |
| `state` | text | `on`, `paused`, or `off` (GAME-100) |
| `wrapped_unlocked` | boolean | WRAP-002 |
| `redemption_closed_at` | timestamp, nullable | Set when an admin closes sticker redemption on Sunday (GAME-078) |
| `updated_at`, `updated_by` | timestamp, staff ID | Every change is also audited |

- **DATA-013** [LOCKED] GameState has exactly one row. A check constraint keeps `state` to the three allowed values.

### Session (a talk or workshop in the program)

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `public_id` | text | Unique, used in the check-in QR (ARCH-020) |
| `title` | text | Entered by an admin |
| `ended_at` | timestamp, nullable | Set by "End session" (GAME-026). Check-in opens then |
| `checkin_closed_at` | timestamp, nullable | Set when the admin closes check-in (GAME-024) |
| `starts_at` | timestamp, nullable | Entered by an admin. The server pauses the game then (GAME-107). Admin only (DATA-014) |

- **DATA-014** [LOCKED] The Session table holds no room names or places (SAFE-037). It holds a title and an optional start time for auto-pause (GAME-107, DEC-051). Start times are seen only by admins, never by players or on the main screen.

### Connection

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `player_low_id` | integer | The smaller of the two player IDs |
| `player_high_id` | integer | The larger of the two player IDs |
| `scanner_id` | integer | Who scanned |
| `question_category` | text | Icebreaker question shown to both, as a key from `icebreaker.categories` (GAME-019), for example `verse` |
| `is_same_church` | boolean | Decides 2 or 10 points |
| `created_at` | timestamp | |

### IcebreakerAnswer

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `connection_id` | integer | Foreign key |
| `about_player_id` | integer | Whose answer this is |
| `typed_by_player_id` | integer | Who typed it: the other person in the pair (GAME-015) |
| `answer_text` | text | Visible to the two people only (SAFE-006). A verse is always saved as full book name, a space, then chapter:verse, for example "John 3:16", so Wrapped can match it exactly (WRAP-012) |

### ChurchMet (for the new church bonus)

| Field | Type | Notes |
|---|---|---|
| `player_id` | integer | The player who got the bonus |
| `church_id` | integer | The church that was new to them |
| `connection_id` | integer | The connection that earned it |

### CheckIn

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `player_id`, `session_id` | integer | |
| `scan_order` | integer | 1 for the first saved check-in in that session (GAME-025) |
| `created_at` | timestamp | |

### Takeaway

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `player_id`, `session_id` | integer | |
| `text` | text | At least 15 words (GAME-030) |
| `visibility` | text | `private`, `shared_named`, or `shared_anonymous` (GAME-031) |
| `review_status` | text | `not_needed` (private), `pending`, `approved`, `rejected`, `hidden` |
| `reviewed_by`, `reviewed_at` | staff ID, timestamp | Nullable |

### Booth, BoothVisit, PhotoboothVisit, HiddenItem

| Table | Key fields | Notes |
|---|---|---|
| Booth | `id`, `name` | Entered by an admin |
| BoothVisit | `player_id`, `booth_id`, `recorded_by`, `created_at` | |
| PhotoboothVisit | `player_id`, `event_day`, `recorded_by`, `created_at` | `event_day` is the date in the venue timezone (GAME-042) |
| HiddenItem | `id`, `item_number`, `claimed_by`, `claimed_at`, `recorded_by` | No location field, ever (SAFE-010) |

### StickerClaim

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `player_id` | integer | |
| `claim_number` | integer | 1, 2, or 3 for that player |
| `recorded_by` | staff ID | The usher who handed over the pack |
| `created_at` | timestamp | |

### PointLedger

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `player_id` | integer | |
| `amount` | integer | Positive for awards, negative for admin revocations |
| `reason_code` | text | For example `connect_other_church`, `checkin`, `manual_award`, `manual_revoke` |
| `source_type`, `source_id` | text, integer | The record that earned it, for example `connection`, 42 |
| `note` | text, nullable | Required for manual awards and revocations (GAME-111) |
| `created_by` | staff ID, nullable | Null when the system awarded it |
| `created_at` | timestamp | |

### AuditLog

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `actor_type`, `actor_id` | text, integer | `system`, `player`, `usher`, `admin`, `screen` |
| `action` | text | For example `pause`, `review_approve`, `pin_reset` |
| `target_type`, `target_id` | text, integer | |
| `reason` | text, nullable | |
| `created_at` | timestamp | |

- **DATA-015** [LOCKED] AuditLog rows are never updated or deleted by the app, only by the retention cleanup (SAFE-014).

## 3. Constraints that enforce game rules

| Rule | Constraint | Enforces |
|---|---|---|
| **DATA-020** [LOCKED] | Connection: `UNIQUE (player_low_id, player_high_id)` and `CHECK (player_low_id < player_high_id)` | Each pair once, no self-connection (GAME-013, GAME-014) |
| **DATA-021** [LOCKED] | ChurchMet: `UNIQUE (player_id, church_id)` | New church bonus once per church per player (GAME-011) |
| **DATA-022** [LOCKED] | CheckIn: `UNIQUE (player_id, session_id)` and `UNIQUE (session_id, scan_order)` | Once per session, and a clean scan order (GAME-023, GAME-025) |
| **DATA-023** [LOCKED] | Takeaway: `UNIQUE (player_id, session_id)` | One takeaway per session (GAME-030) |
| **DATA-024** [LOCKED] | BoothVisit: `UNIQUE (player_id, booth_id)` | Once per booth (GAME-041) |
| **DATA-025** [LOCKED] | HiddenItem: `UNIQUE (item_number)`, and `claimed_by` can be set only once | Each item claimed once in total (GAME-043) |
| **DATA-026** [LOCKED] | StickerClaim: `UNIQUE (player_id, claim_number)` | No double claims (GAME-074) |
| **DATA-027** [LOCKED] | PointLedger: `UNIQUE (player_id, reason_code, source_type, source_id)` for system awards | The same record never pays twice |

Rules that a unique constraint cannot express are checked by the points service inside the same transaction (ARCH-040):

- **DATA-028** [LOCKED] Photobooth cap: count that player's PhotoboothVisit rows for that `event_day` before inserting (GAME-042).
- **DATA-029** [LOCKED] Sticker cap and stock: `claim_number` must be at most `stickers.max_per_player` and at most the stickers earned. Total claims must stay under `stickers.stock_total` once that is set (GAME-071, GAME-074, GAME-076).

## 4. Score

- **DATA-030** [LOCKED] A player's score is the sum of `amount` in PointLedger for that player. Nothing else stores the score as a separate number that could drift. A cached total is allowed only if it is updated in the same transaction as the ledger row.
- **DATA-031** [LOCKED] Stickers earned is computed from score (GAME-070). It is not stored.

## 5. Open items

- **DATA-010** [PROPOSED] Region data is not collected. Wrapped has no regions number (WRAP-011), so the church list needs no region column. The `region` column stays, unused. Removing it needs its own migration PR (DEC-048).
- **DATA-040** [PROPOSED] Migrations are numbered plain SQL files, run in order by a small runner in the app. No migration library (ENG-050, DEC-027).
