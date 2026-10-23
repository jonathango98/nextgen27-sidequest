# 11 Operations Runbook

- Status: Active (each rule has its own status)
- Owner: Jonathan (@jonathango98)
- Version: 1.1.0
- Last updated: 2026-10-23

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file is for game day and the weeks before it: who does what, what to do when something breaks, and the checklists. It holds no names, contact details, room numbers, or item locations. Those live with the real event data (section 6).

## 1. Game-day roles

| Role | How many | Main jobs |
|---|---|---|
| Game director | 1 | Runs the game, makes calls on rules during the event, hands out prizes on Sunday |
| Admin | Set by Jonathan | Pause and resume, end sessions, review takeaways, fix scores, reset PINs |
| Usher | 5 to 10 | Game booth and sticker line, booth scans, hidden items, photobooth, helping people join |
| Developer on call | At least 1 | Watches the server, fixes urgent bugs (only with an approved issue during freeze, ENG-071) |

- **OPS-001** [LOCKED] An admin pauses the game at the start of every session (GAME-101). Until an automatic schedule is decided (GAME-107), this is done by hand.
- **OPS-002** [LOCKED] When a session ends, an admin presses "End session". That opens check-in and resumes the game (GAME-026). The hall screen then shows the rotating check-in code (GAME-020).
- **OPS-003** [LOCKED] During breaks, at least 2 ushers work the game booth, with a separate line for sticker claims.
- **OPS-004** [LOCKED] Sticker packs are pre-packed and sealed before the event.
- **OPS-005** [PROPOSED] At the end of each game day, an admin sets the game to off until game hours are decided (GAME-106).

## 2. Usher tasks

| Task | Steps | Rule |
|---|---|---|
| Booth visit | Pick the booth, scan the player's My Code, check the green message | GAME-041 |
| Photobooth | Scan My Code after the photo. If it says "daily limit", explain kindly | GAME-042 |
| Hidden item | Take the item, type its number, scan My Code, keep the item at the booth | GAME-043 |
| Sticker claim | Scan My Code, check that the screen says "1 sticker to claim" (or more), hand over one sealed pack per claim | GAME-073 |
| Help someone join | Show them the join QR or link, help them pick their church, remind them to remember their PIN | SAFE-002 |
| Dead phone | Look the player up by full name, check their name badge, record the quest | GAME-113 |
| Locked PIN | Send the player to an admin. Ushers cannot reset PINs | SAFE-023 |

## 3. Admin tasks

| When | Task | Rule |
|---|---|---|
| Day 1, before the intro | Check the church list, booths, item numbers, sessions, and staff accounts are loaded. Game state: paused | GAME-110 |
| Day 1, after the intro | Set the game to on | GAME-104 |
| Start of every session | Pause | OPS-001 |
| End of every session | End session (opens check-in, resumes) | OPS-002 |
| During breaks | Work the review queue. Check unusual activity | SAFE-007, ARCH-062 |
| Any time | Fix scores with a reason. Reset locked PINs after checking the badge | GAME-111, SAFE-044 |
| End of each game day | Set the game to off | OPS-005 |
| Sunday | Game off. Show results. Run the conference recap. Unlock Wrapped right after results | GAME-104, WRAP-002, WRAP-020 |

## 4. Failure playbook

- **OPS-020** [LOCKED] Use this table when something goes wrong. Write down what happened (time, what you saw) for the post-event review. Never post real names in issues (SAFE-036).

| Problem | What to do now | Who | Later |
|---|---|---|---|
| Wi-Fi down or very slow | Switch to the backup router if available. Ushers use the paper log: full name, church, quest (ARCH-081) | Developer on call, ushers | An admin enters the paper log as manual awards with reason "paper fallback" |
| Server down | Pause announcements about the game. Ushers use the paper log | Developer on call | Check backups, enter the paper log |
| Dead phone or no battery | Usher looks the player up by name and records the quest (GAME-113) | Usher | |
| Wrong score | Admin checks the player's history and makes a manual award or revocation with a reason | Admin | If it is a bug, open an issue with fake data |
| Long booth line | Use the separate sticker line. Add a second usher | Usher lead | |
| Stickers run out | The server refuses new claims (GAME-076). Ushers explain kindly | Ushers | |
| Locked PIN | Admin checks the name badge, then resets (SAFE-044) | Admin | |
| Forgot to pause | Pause now. Then decide whether to revoke points earned during the session | Admin, game director | |
| Unusual activity (possible fake accounts) | Look at the activity view. Do not accuse anyone in public | Admin, game director | Before prizes, check top players in person (GAME-090) |
| Concerning takeaway | Do not approve it. Tell the organizer responsible for child safety in person (SAFE-042) | Admin | Follow the organization's child safety policy |
| Main screen frozen | Reload the page. If it is still stuck, log in again in screen mode | Admin | |
| Secret or real data posted on GitHub | Tell Jonathan right away (SAFE-034) | Whoever saw it | Jonathan rotates and cleans up |

## 5. Checklists

### Pre-event (two weeks before, after code freeze)

- [ ] Production on Railway is up, HTTPS works, and staging matches production (ARCH-010, ARCH-011)
- [ ] Secrets are set as environment variables on the server, not in any file in the repo (SAFE-032)
- [ ] Backups run and a restore was tested (ARCH-053)
- [ ] Church list loaded. Booths loaded. Hidden item numbers loaded (no locations in the app, SAFE-010)
- [ ] Session titles loaded (no room details, DATA-014)
- [ ] Usher and admin accounts created, one per person (ARCH-036)
- [ ] Usher training done (OPS-010)
- [ ] Paper fallback kit printed: blank paper logs and pens (ARCH-081)
- [ ] Sticker packs sealed and counted, and `stickers.stock_total` set (GAME-069)
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
- database files and backups
- any schedule that ties sessions to rooms

- **OPS-040** [OPEN] Where real event data is stored. The planned default was a private Google Drive folder owned by Jonathan. Jonathan decides the final location. Until then, ask Jonathan before saving real event data anywhere.
- **OPS-041** [LOCKED] Whatever the location: real event data never goes in this repo, in issues, in PR comments, or in screenshots (SAFE-030). Access is limited to the people who need it. Links to it are never posted in the repo.
- **OPS-042** [LOCKED] After the retention date (SAFE-014), real event data is deleted from that location and from the server and backups. Staff accounts are switched off after the event.
