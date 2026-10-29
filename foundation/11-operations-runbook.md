# 11 Operations Runbook

- Status: Active (each rule has its own status)
- Owner: Jonathan (@jonathango98)
- Version: 1.3.0
- Last updated: 2026-10-28

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file is for game day and the weeks before it: who does what, what to do when something breaks, and the checklists. It holds no names, contact details, room numbers, or item locations. Those live with the real event data (section 6).

## 1. Game-day roles

| Role | How many | Main jobs |
|---|---|---|
| Game director | 1 | Runs the game, makes calls on rules during the event, hands out prizes on Sunday |
| Admin | Set by Jonathan | Pause and resume, end sessions, review takeaways, fix scores, reset PINs |
| Usher | 5 to 10 | Game booth and blind box line, booth scans, hidden items, photobooth, helping people join |
| Developer on call | At least 1 | Watches the server, fixes urgent bugs (no production deploys during live game hours, ARCH-016) |

- **OPS-001** [LOCKED] An admin pauses the game at the start of every session (GAME-101). The timetable schedule (GAME-107) is only a backup, so this is still done by hand.
- **OPS-002** [LOCKED] When a session ends, an admin presses "End session". That resumes the game and opens takeaways for that session (GAME-026). Check-in already happened before the session (GAME-021).
- **OPS-003** [LOCKED] During breaks, at least 2 ushers work the game booth, with a separate line for blind box claims.
- **OPS-004** [LOCKED] Blind boxes are pre-packed and sealed before the event.
- **OPS-005** [PROPOSED] At the end of each game day, an admin sets the game to off. There are no automatic game hours (GAME-106).
- **OPS-006** [PROPOSED] Before each session, check that the hall screen shows the check-in code. It opens on its own from the session's start time and check-in minutes (GAME-021). For a session with no start time, an admin presses "Open check-in" (GAME-027). The game must be on, or every scan is refused (GAME-102, GAME-108).

## 2. Usher tasks

| Task | Steps | Rule |
|---|---|---|
| Booth visit | Pick the booth, scan the player's My Code, check the green message | GAME-041 |
| Photobooth | Scan My Code after the photo. If it says "daily limit", explain kindly | GAME-042 |
| Hidden item | Take the item, type its number, scan My Code, keep the item at the booth | GAME-043 |
| Blind box claim | Scan My Code, check that the screen says "1 box to claim" (or more), hand over one sealed blind box per claim | GAME-073 |
| Help someone join | Show them the join QR or link, help them pick their church, remind them to remember their PIN | SAFE-002 |
| Dead phone | Look the player up by full name, check their name badge, record the quest | GAME-113 |
| Locked PIN | Send the player to an admin. Ushers cannot reset PINs | SAFE-023 |

## 3. Admin tasks

| When | Task | Rule |
|---|---|---|
| Day 1, before the intro | Check the church list, booths, item numbers, sessions with start times and check-in minutes, and staff accounts are loaded. Game state: paused | GAME-110, GAME-107 |
| Day 1, after the intro | Set the game to on | GAME-104 |
| Day 2, before the first session | Set the game from off to on before the first check-in opens. Auto-pause then pauses each session (it never acts while off) | GAME-104, GAME-107 |
| Before every session | Check-in opens on its own. No start time: press Open check-in. Check the hall screen shows the code | OPS-006 |
| Start of every session | Pause | OPS-001 |
| End of every session | End session (resumes, opens takeaways) | OPS-002 |
| During breaks | Work the review queue. Check unusual activity | SAFE-007, ARCH-062 |
| Any time | Fix scores with a reason. Reset locked PINs after checking the badge | GAME-111, SAFE-044 |
| End of each game day | Set the game to off | OPS-005 |
| Sunday | Game off. Blind box claims stay open until the service, then close redemption. Show results. Run the conference recap. Unlock Wrapped right after results | GAME-104, GAME-078, WRAP-002, WRAP-020 |

## 4. Failure playbook

- **OPS-020** [LOCKED] Use this table when something goes wrong. Write down what happened (time, what you saw) for the post-event review. Never post real names in issues (SAFE-036).

| Problem | What to do now | Who | Later |
|---|---|---|---|
| Wi-Fi down or very slow | Switch to the backup router if available. Ushers use the paper log: full name, church, quest (ARCH-081) | Developer on call, ushers | An admin enters the paper log as manual awards with reason "paper fallback" |
| Server down | Pause announcements about the game. Ushers use the paper log | Developer on call | Check backups, enter the paper log |
| Dead phone or no battery | Usher looks the player up by name and records the quest (GAME-113) | Usher | |
| Wrong score | Admin checks the player's history and makes a manual award or revocation with a reason | Admin | If it is a bug, open an issue with fake data |
| Long booth line | Use the separate blind box line. Add a second usher | Usher lead | |
| Blind boxes run out | The server refuses new claims (GAME-076). Ushers explain kindly | Ushers | |
| Locked PIN | Admin checks the name badge, then resets (SAFE-044). Or the player waits: the account unlocks itself after 60 minutes (SAFE-022) | Admin | |
| Game left on overnight | Set the game to off now (OPS-005). Then decide whether to revoke points earned overnight | Admin, game director | |
| Forgot to pause | Pause now. Then decide whether to revoke points earned during the session | Admin, game director | |
| Unusual activity (possible fake accounts) | Look at the activity view. Do not accuse anyone in public | Admin, game director | Before prizes, check top players in person (GAME-090) |
| Concerning takeaway | Do not approve it. Tell the organizer responsible for child safety in person (SAFE-042) | Admin | Follow the organization's child safety policy |
| Main screen frozen | Reload the page. If it is still stuck, log in again in screen mode | Admin | |
| Secret or real data posted on GitHub | Tell Jonathan right away (SAFE-034) | Whoever saw it | Jonathan rotates and cleans up |

## 5. Checklists

### Pre-event (two weeks before the event)

- [ ] Production on Railway is up, HTTPS works, and staging matches production (ARCH-010, ARCH-011)
- [ ] Secrets are set as environment variables on the server, not in any file in the repo (SAFE-032)
- [ ] Backups run and a restore was tested (ARCH-053)
- [ ] Church list loaded. Booths loaded. Hidden item numbers loaded (no locations in the app, SAFE-010)
- [ ] Session titles and start times loaded (no room details, DATA-014, GAME-107)
- [ ] Usher and admin accounts created, one per person (ARCH-036)
- [ ] Usher training done (OPS-010)
- [ ] Paper fallback kit printed: blank paper logs and pens (ARCH-081)
- [ ] Blind boxes sealed and counted, and `blind_box.stock_total` set (GAME-069)
- [ ] Join QR on the intro slides points to the production sign-up page (ARCH-024)
- [ ] Main screen device and hall screens tested in screen mode (ARCH-037)

### Venue walkthrough (mid-February)

- **OPS-030** [LOCKED] At the venue walkthrough, the team checks:
  - [ ] Hotel Wi-Fi load test of the join moment, about 300 phones (ARCH-071)
  - [ ] Backup router tested
  - [ ] Main screen readable from the back of the ballroom (UI-041)
  - [ ] Where the hall screens for check-in codes will be (GAME-020)
  - [ ] Hidden item spots are in conference areas only, never guest floors, restrooms, stairwells, or parking (SAFE-026)
  - [ ] Game booth location and space for two lines (OPS-003)

- **OPS-010** [LOCKED] Ushers are confirmed in late January and trained in February.

## 6. Where real event data lives

Real event data is any information about real people or the real venue. Examples:
- attendee exports (names, churches, under-18 answers)
- the usher roster and volunteer contact details
- the hidden item list and where each item is hidden
- playtest results and notes about real players
- database exports (database files and backups stay on the server, ARCH-052, ARCH-053)
- any schedule that ties sessions to rooms

- **OPS-040** [LOCKED] Real event data is stored in a private Google Drive folder owned by Jonathan, shared only with the people who need it (DEC-049). Ask Jonathan for access.
- **OPS-041** [LOCKED] Whatever the location: real event data never goes in this repo, in issues, in PR comments, or in screenshots (SAFE-030). Access is limited to the people who need it. Links to it are never posted in the repo.
- **OPS-042** [LOCKED] After the retention date (SAFE-014), real event data is deleted from that location and from the server and backups. Staff accounts are switched off after the event.
