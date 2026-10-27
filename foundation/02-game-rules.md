# 02 Game Rules

- Status: Active (each rule has its own status)
- Owner: Jonathan (@jonathango98)
- Version: 1.1.0
- Last updated: 2026-10-27

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file says how the game works: every quest, every number, every limit, and what happens in edge cases. Every number here also lives in `foundation/game-config.yaml`. The config file is the source of truth. Code reads numbers from config, never from this file and never from a hardcoded value.

Status words: LOCKED (build it), PROPOSED (build against it, may change after a playtest), OPEN (not decided, do not build behavior that depends on it). See `foundation/README.md`.

## 1. Core rules

- **GAME-001** [LOCKED] Every player has a personal QR code called My Code. It changes every 30 seconds, so a screenshot stops working quickly. Config: `qr.rotation_seconds`.
- **GAME-002** [LOCKED] The server is the only authority for points. The phone never decides who earns what. The phone only sends what was scanned or typed, and the server checks everything.
- **GAME-003** [LOCKED] Points are the only currency. A player's points total is called their score. There are no coins. Score moves the player leaderboard and the church leaderboard, and it unlocks blind boxes (section 6).
- **GAME-004** [LOCKED] Score never goes down, with one exception: an admin revokes points by hand (GAME-111). Claiming a blind box never lowers score.
- **GAME-005** [LOCKED] Connections have no limit. Every other quest has a limit.
- **GAME-006** [PROPOSED] All point values in this file are proposals. The game director adjusts them after Playtest 1 by changing `game-config.yaml`.

## 2. Quest table

This is the full list of ways to earn points. If an action is not in this table, it earns nothing.

| Category | Quest | Rule | Points | Config key | Limit | Who confirms |
|---|---|---|---|---|---|---|
| Connect | Meet someone from another church | GAME-010 | 10 each (both players) | `points.connect_other_church` | Each pair once | Scan, then each player types their answer (GAME-016) |
| Connect | First person met from a church new to you | GAME-011 | 5 (bonus) | `points.connect_new_church_bonus` | Once per church, per player | Automatic |
| Connect | Meet someone from your own church | GAME-012 | 2 each | `points.connect_same_church` | Each pair once | Scan, then each player types their answer (GAME-016) |
| Sessions | Session check-in | GAME-020 | See check-in tiers | `checkin.tier_points` | Once per session | Player scans the hall screen |
| Sessions | Journal takeaway | GAME-030 | 20 | `points.journal_takeaway` | Once per session | Server checks word count |
| Explore | Join the game | GAME-040 | 10 | `points.join` | Once | Automatic at sign-up |
| Explore | Booth visit | GAME-041 | 10 | `points.booth_visit` | Once per booth | Usher scans My Code |
| Explore | Photobooth | GAME-042 | 5 | `points.photobooth` | 5 per day | Usher scans My Code |
| Explore | Hidden item | GAME-043 | 15 | `points.hidden_item` | Each item once in total | Usher at the game booth |

### Check-in tiers

| Scan order in that session | Points | Config key |
|---|---|---|
| 1 to 10 | 25 | `checkin.tier_points` (1st value) |
| 11 to 20 | 20 | `checkin.tier_points` (2nd value) |
| 21 to 30 | 15 | `checkin.tier_points` (3rd value) |
| 31 to 40 | 10 | `checkin.tier_points` (4th value) |
| 41 and after | 5 | `checkin.tier_points` (5th value) |

Tier size: 10 scans per tier. Config: `checkin.tier_size`.

### Other limits

| Limit | Value | Config key | Rule |
|---|---|---|---|
| Photobooth visits that earn points, per player per day | 5 | `limits.photobooth_per_day` | GAME-042 |
| Minimum words in a takeaway | 15 | `limits.journal_min_words` | GAME-030 |
| Points per blind box milestone | 300 | `blind_box.milestone_points` | GAME-070 |
| Most blind boxes per player | 3 | `blind_box.max_per_player` | GAME-071 |
| My Code and check-in code rotation, in seconds | 30 | `qr.rotation_seconds` | GAME-001 |

## 3. Connect

- **GAME-010** [PROPOSED] When two players from different churches connect, each player earns 10 points when they type their icebreaker answer (GAME-016).
- **GAME-011** [PROPOSED] A player earns a 5 point bonus the first time they connect with anyone from a church they have not met before. It is given with the first icebreaker answer the player types for someone from that church (GAME-016). The bonus is judged for each player on their own. One player can get the bonus while the other does not (see example E1).
- **GAME-012** [PROPOSED] When two players from the same church connect, each player earns 2 points when they type their icebreaker answer (GAME-016). This stays low so a group cannot pad scores by scanning each other.
- **GAME-013** [LOCKED] Each pair of players counts once, no matter who scans whom or how many times. Alice scanning Ben and Ben scanning Alice is the same pair.
- **GAME-014** [LOCKED] A connection starts when one player scans the other player's My Code with the in-app scanner. A player cannot connect with themselves. An expired code is refused (see ARCH-022).
- **GAME-015** [PROPOSED] Who types the icebreaker answer: each person types the other person's answer on their own phone (option A, conflict C5, DEC-042). Config: `icebreaker.who_types`.
- **GAME-016** [PROPOSED] Each player earns their connection points when they save the answer they type (the IcebreakerAnswer row where `typed_by_player_id` is them). They never wait on the other phone, so a player who doesn't type only misses their own points. There is no time limit. Until a player types, the connection exists (GAME-013) but earns them nothing. Typing the answer earns points, so it follows the pause and off rules (GAME-102, GAME-108) (DEC-042). Config: `icebreaker.award_trigger`.
- **GAME-017** [LOCKED] After a scan, both phones show the same icebreaker question, for example "Favorite food?" or "Favorite verse?". The answers are visible only to the two people (SAFE-006).
- **GAME-018** [LOCKED] "Another church" means the church each player picked from the church list at sign-up (SAFE-002). Who can change a player's church later is in DATA-012.
- **GAME-019** [PROPOSED] Each pair gets one question picked at random from the pool below. It is a starter pool for the game director to edit before core build ends (DEC-042). Wrapped counts the verse and food answers (WRAP-012). Config: `icebreaker.categories`.

| Category | Question | Answer |
|---|---|---|
| verse | Favorite Bible verse? | Book, chapter, and verse pickers (WRAP-012) |
| food | Favorite food? | Free text |
| game | Best youth group game you've played? | Free text |
| song | A worship song you can't stop singing? | Free text |
| place | Dream place to visit? | Free text |
| hobby | What do you do for fun? | Free text |

## 4. Sessions

### Check-in

- **GAME-020** [LOCKED] Each session has a check-in QR code. It is shown on a screen inside the hall, not printed. It rotates every 30 seconds like My Code, so a photo of it stops working quickly. Config: `qr.rotation_seconds`.
- **GAME-021** [LOCKED] The check-in code goes live only when the admin ends the session. Leaving early earns nothing.
- **GAME-022** [PROPOSED] The first players to check in earn the most. Points follow the tier table in section 2. Config: `checkin.tier_size`, `checkin.tier_points`.
- **GAME-023** [LOCKED] Each player can check in once per session.
- **GAME-024** [PROPOSED] Check-in stays live for 10 minutes after the admin ends the session, then closes on its own. An admin can still close it early by hand (DEC-041). Config: `checkin.auto_close_minutes`.
- **GAME-025** [PROPOSED] Scan order is the order in which the server saves check-ins for that session. The 11th saved check-in gets tier 2 points, even if two phones scanned in the same second.
- **GAME-026** [PROPOSED] The admin action "End session" does two things in one step: it opens check-in for that session and turns the game from paused to on.

### Journal

- **GAME-030** [PROPOSED] A player earns 20 points for a takeaway of at least 15 words, once per session. Config: `points.journal_takeaway`, `limits.journal_min_words`.
- **GAME-031** [LOCKED] The player chooses who can see each takeaway: private, shared with name, or shared anonymously. Points are the same for every choice, so nobody shares publicly just for points.
- **GAME-032** [PROPOSED] Points are given when the takeaway is submitted. Review only controls whether a shared post becomes visible (SAFE-007). An admin can revoke points for a junk entry (GAME-111).
- **GAME-033** [LOCKED] Takeaways cannot be submitted while the game is paused. Config: `journal.allow_while_paused`.
- **GAME-034** [PROPOSED] Words are counted by splitting the text on spaces and line breaks. "God is good" is 3 words. Punctuation alone, like "-", does not count as a word.
- **GAME-035** [PROPOSED] A player does not need to check in to a session to write a takeaway for it, but the session must have ended (GAME-026, DEC-051). There is no deadline beyond the pause and off rules (GAME-033, GAME-108). Points stay once per session (GAME-030) (DEC-047). Config: `journal.require_checkin`.
- **GAME-036** [PROPOSED] A player can write a takeaway only for a session that the admin has ended.

## 5. Explore

- **GAME-040** [PROPOSED] A player earns 10 points for joining the game. This is given once per player, on any day they join. Config: `points.join`.
- **GAME-041** [PROPOSED] A player earns 10 points per booth visit, once per booth. An usher at the booth scans the player's My Code. Examples of booths: the mission booth and the merch table. The booth list is entered by an admin before the event. Config: `points.booth_visit`.
- **GAME-042** [PROPOSED] A player earns 5 points per photobooth visit, up to 5 visits per day. An usher scans My Code. The day boundary is midnight in the venue timezone (GAME-105). Config: `points.photobooth`, `limits.photobooth_per_day`.
- **GAME-043** [PROPOSED] Numbered hidden items are placed in conference areas only (SAFE-010). A player who finds one brings it to the game booth. An usher records the item number and scans the player's My Code. The player earns 15 points. Each item can be claimed once in total, by the first player who turns it in. The booth keeps the item. Config: `points.hidden_item`.
- **GAME-044** [PROPOSED] Join points are given at sign-up even while the game is paused, so players see their first points during the Day 1 stage intro. This is the only earning allowed while paused (GAME-102, DEC-043). Config: `join.points_while_paused`.
- **GAME-045** [PROPOSED] The game booth does not count as a booth for GAME-041 (DEC-040).

## 6. Blind boxes

Blind boxes replace the coin system from the Blueprint (DEC-002). They replaced stickers (DEC-052). Score unlocks blind boxes. Nothing is spent.

- **GAME-070** [PROPOSED] A player earns one blind box every 300 points of score. Blind boxes earned = score divided by 300, rounded down, capped at the max (GAME-071). This is computed from score every time. Nothing is stored or reset. The progress bar on the phone shows points since the last milestone, for example 120 of 300. Config: `blind_box.milestone_points`.
- **GAME-071** [PROPOSED] A player can earn at most 3 blind boxes. Config: `blind_box.max_per_player`.
- **GAME-072** [LOCKED] Each blind box is a sealed box with a mystery item inside. What goes inside is OPEN (GAME-068). All milestone rewards are blind boxes. There are no separate milestone rewards and no "Side Quest Legend" (DEC-052).
- **GAME-068** [OPEN] What goes inside a blind box. Owner: game director. Building the claim flow does not depend on it (DEC-052).
- **GAME-073** [LOCKED] To claim: the player taps Open Box in the app, goes to the game booth while redemption is open (GAME-078), an usher scans their My Code, the usher hands over a sealed blind box, and the claim is saved. Tapping Open Box does not reserve a box. It only opens the claim screen.
- **GAME-074** [LOCKED] Blind boxes the player can claim now = blind boxes earned minus blind boxes already claimed. This is never below 0.
- **GAME-075** [LOCKED] Claims happen during breaks only. The booth closes during sessions, so the server refuses claims while the game is paused. On Sunday the game is off, but claims stay open until the service (GAME-078).
- **GAME-076** [LOCKED] Blind boxes are limited and first come, first served. When they run out, they are gone. When claims reach the stock number (GAME-069), the server refuses new claims with `OUT_OF_STOCK`.
- **GAME-069** [OPEN] The number of blind boxes. It comes from the final blind box order. Until it is set, the server does not limit claims by stock. Config: `blind_box.stock_total`.
- **GAME-077** [LOCKED] There is no "boxes left" counter anywhere: not on the main screen, not in the app. Config: `blind_box.live_counter`.
- **GAME-078** [PROPOSED] Claims are open on Day 1 evening, during Day 2 breaks, and on Sunday before the service (option B, DEC-045). On Sunday the game is off, so nothing earns points, but blind box claims still work until an admin taps Close redemption when the service starts (GAME-110, DEC-051). Unclaimed blind boxes are lost when redemption closes. Config: `blind_box.redemption_window`.
- **GAME-079** [PROPOSED] No blind box trading (option B, DEC-040). Config: `blind_box.trading`.
- **GAME-080** [PROPOSED] The blind box order is about 450 boxes. This is an estimate. Recalculate after Playtest 1 (conflict C6).

The Blueprint's estimated share of players at each level (indicative only, conflict C6). It assumed 15 points per connection and a +10 bonus. With the current values (10 and +5), fewer players reach each level.

| Blind boxes earned | Score range | Estimated share of players |
|---|---|---|
| 0 | 0 to 299 | about 29% |
| 1 | 300 to 599 | about 34% |
| 2 | 600 to 899 | about 23% |
| 3 | 900 and up | about 14% |

## 7. Leaderboards and church score

- **GAME-081** [LOCKED] Church score is a fair average of points per player, so a church of 5 can compete with a church of 40 and one very active player cannot carry a church alone. The formula is in GAME-089 (DEC-044).
- **GAME-089** [PROPOSED] Church score is a shrunk average (conflict C4, DEC-044). It counts the church's active players: players with points from anything other than joining (GAME-040, DEC-053). Church score = (their points added up + k × overall average) ÷ (their number + k), where the overall average is over every active player and k is 5. This counts each church as if it also had k average players, so a small church can still win, but not on one lucky player. It is shown rounded to a whole number. Config: `leaderboard.church_score_denominator`, `leaderboard.church_score_prior_players`.
- **GAME-082** [PROPOSED] A church needs 1 active player (GAME-089) to appear on the church leaderboard. GAME-089 stops a small church from topping the board on one player (DEC-041, DEC-053). Config: `leaderboard.church_min_players`.
- **GAME-083** [PROPOSED] Each main screen leaderboard shows 10 rows (DEC-041). Config: `leaderboard.main_screen_top_n`.
- **GAME-084** [PROPOSED] Ties go to whoever reached that score first: the earlier latest point award ranks higher. Church ties use the latest point award of any counted player. This applies to boards and prizes (DEC-041). Config: `leaderboard.tie_break`.
- **GAME-085** [PROPOSED] The phone shows no leaderboard and no rank, only the player's own points. Leaderboards are on the main screen only (DEC-040). Config: `leaderboard.in_app_leaderboard`.
- **GAME-086** [LOCKED] The player leaderboard shows first name, last initial, and church (SAFE-004, GAME-088). Under-18 players appear like everyone else (SAFE-019).
- **GAME-087** [LOCKED] Leaderboards appear on the main screen only between sessions, never during a talk (UI-040).
- **GAME-088** [PROPOSED] Every row on a player leaderboard shows the last initial after the first name, for example "Sam K." (DEC-046). This tells apart most players with the same first name and church. It changed SAFE-004, so it went through safety review (SAFE-016).

Church score example (GAME-089). The overall average is 90. Example Church A has 5 players with scores 100, 80, 60, 10, 10. The two with 10 only joined, so 3 active players count.

| Step | Calculation | Result |
|---|---|---|
| Plain average of counted players | (100 + 80 + 60) / 3 | 80 |
| Church score, k = 5 | (240 + 5 × 90) / (3 + 5) | 86 |

Example Church B has 1 player with 300 points. Its church score is (300 + 5 × 90) / (1 + 5) = 125, not 300.

## 8. Prizes

- **GAME-090** [LOCKED] Prizes are given at the Sunday service and claimed in person. This stops fake accounts from winning.
- **GAME-091** [PROPOSED] No raffle. Prizes go by rank only (DEC-040). Config: `prizes.raffle`.
- **GAME-092** [OPEN] The final prize list (for example top player and top church) and whether prizes come from the game budget or another budget. Owner: game director and leadership. Config: `prizes.categories`.

## 9. Game states and pause

- **GAME-100** [LOCKED] The game is always in one of three states: on, paused, or off. Config: `game.states`.
- **GAME-101** [LOCKED] The game is paused during every session. An admin turns pause on and off by hand.
- **GAME-102** [LOCKED] While paused, the server refuses every action that earns points or claims a blind box, with the "paused" response (API-020). This includes connection scans, saving an icebreaker answer, check-ins, takeaway submissions, booth scans, photobooth scans, hidden item turn-ins, and blind box claims. While paused, players can still sign up, log in, view My Code, read their own data, and read the summary page. The one exception to refusing is join points at sign-up (GAME-044).
- **GAME-103** [LOCKED] Admin fixes work in every state. An admin can award or revoke points by hand at any time, including while paused or off.
- **GAME-104** [LOCKED] Day by day: Day 1 evening the game is on after the stage intro. Day 2 the game is on during breaks and paused during sessions. Day 3 (Sunday) the game is off: no gameplay, only final results, prizes, and Wrapped.
- **GAME-105** [PROPOSED] The venue is in Houston, Texas, so the timezone is `America/Chicago` (DEC-050). The server stores all times in UTC and uses this timezone for "per day" limits (GAME-042). Config: `game.timezone`.
- **GAME-106** [PROPOSED] No automatic game hours. An admin sets the game to off at the end of each game day by hand (OPS-005, SAFE-027, DEC-049). Owner: leadership. Config: `game.hours_window`.
- **GAME-108** [PROPOSED] While the game is off, the server refuses every earning action and blind box claim with `GAME_OFF` (API-020). Sign-up is closed. Login, the player's own data, the summary page, and Wrapped (after unlock) still work. Blind box claims also still work inside the redemption window (GAME-078).
- **GAME-107** [PROPOSED] An admin enters a start time with each session, and the server pauses the game at that time, as a backup to manual pause (DATA-014, DEC-051). It acts only while the game is on, so it never turns an off game to paused. It never resumes the game; ending a session does (GAME-026). Admins can still pause and resume by hand, for example when a session runs late (DEC-049). Config: `game.auto_pause_schedule`.

## 10. Admin and usher powers

- **GAME-110** [LOCKED] Admins can: pause and resume the game, set the game to off, end a session (GAME-026), review shared takeaways, award and revoke points by hand, reset a locked PIN (SAFE-023), fix a player's church, manage the church list, booths, hidden item numbers, sessions, and usher accounts, close blind box redemption on Sunday (GAME-078), and unlock Wrapped (WRAP-002).
- **GAME-111** [LOCKED] Every manual award or revocation needs a written reason and writes an audit row (ARCH-050). Revocation is the only action that lowers a score (GAME-004).
- **GAME-112** [LOCKED] Ushers can: scan My Code for booth visits, photobooth visits, hidden item turn-ins, and blind box claims, and look up a player by name to help them. Ushers cannot give arbitrary points. Only admins can (GAME-110).
- **GAME-113** [PROPOSED] If a player's phone is dead, an usher looks the player up by name and records the same quest (booth, photobooth, hidden item, blind box claim) without a scan. The usher's account is saved on the record.
- **GAME-114** [PROPOSED] An admin cannot revoke more points than the player has. Score never goes below 0.

## 11. Removed and parked

- **GAME-050** [LOCKED] These earn no points: prayer, encouragement, and reading the takeaway feed or summary page.
- **GAME-051** [LOCKED] Removed for good: secret words from the stage (nothing should reward opening a phone during a talk), Secret Pastors, and selfie prompts.
- **GAME-120** [PROPOSED] Midday challenge. Not in v1 (conflict C1, DEC-040). Parked design: teams of 4 from 4 different churches, ushers judge, top 3 teams earn +100, +50, +25 per member, which also counts for their church. Config: `features.midday_challenge` (off).
- **GAME-121** [LOCKED] Golden QR drops on the main screen. Not in v1 (conflict C2, DEC-040). Config: `features.golden_qr_drops` (off).
- **GAME-122** [PROPOSED] Players without a phone are not supported in v1. They can attend everything but do not play (DEC-040). Config: `features.no_phone_players` (off).

## 12. Worked examples

All names are fake.

**E1. First connection with a new church (GAME-010, GAME-011).** Test Player A (Example Church A) scans Test Player B (Example Church B). Player A has never met anyone from Church B. Player B has already met someone from Church A. Each player earns when they type their icebreaker answer (GAME-016).

| Player | Base | New church bonus | Total |
|---|---|---|---|
| Test Player A | 10 | 5 | 15 |
| Test Player B | 10 | 0 | 10 |

**E2. Same pair again (GAME-013).** Later, Player B scans Player A. The pair already exists. The server refuses with "already connected" and nobody earns points.

**E3. Same church (GAME-012).** Two players from Example Church A connect. Each earns 2 when they type their answer. No bonus, because their own church is not "new".

**E4. Check-in tiers (GAME-022, GAME-025).** The admin ends Session 3. Test Player C is the 12th check-in the server saves. Player C earns 20 (tier 2).

**E5. Check-in while paused (GAME-102).** The admin ended Session 3 but then paused again by mistake. Player D scans. The server returns "paused" and saves nothing. Player D scans again after the admin resumes.

**E6. Short takeaway (GAME-030).** Player E writes 14 words. The server refuses and says how many more words are needed. Nothing is saved.

**E7. Takeaway while paused (GAME-033).** Player E starts typing during a break, and the next session starts before they submit. Submit returns "paused". The phone keeps the text so they can submit after the session.

**E8. Photobooth cap (GAME-042).** Player F visits the photobooth for the 6th time on Day 2. The usher scan is refused with "daily limit reached". On the next day, Player F can earn again.

**E9. Hidden item claimed once (GAME-043).** Player G turns in item 7 and earns 15. Later, Player H brings in a second item with the number 7 on it. The server refuses because item 7 is already claimed. The usher tells the game director, since a duplicate number means a printing or placement mistake.

**E10. Blind box math (GAME-070, GAME-071, GAME-074).** Player J has 905 points. Blind boxes earned = 905 / 300 = 3 (rounded down). Player J has claimed 1. Player J can claim 2 more. At 1,500 points, blind boxes earned is still 3 (the max).

**E11. Revocation after a claim (GAME-004, GAME-074, GAME-111).** Player K has 610 points, has earned 2 blind boxes, and has claimed 2. An admin revokes 20 points for a junk takeaway, with a reason. Score is now 590. Blind boxes earned is now 1, claimed is still 2, so claimable is 0 (never below 0). Player K keeps both blind boxes. To claim a 3rd, Player K needs 900 points.

**E12. Shared screenshot (GAME-001).** Player L sends a screenshot of their My Code to a friend in another room. After the code rotates and the previous window passes (ARCH-022), a scan of the screenshot is refused with "code expired".

**E13. Joining on Day 2 (GAME-040).** Player M joins on Day 2. Player M earns 10 join points, the same as a Day 1 joiner.
