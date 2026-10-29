# 14 Glossary

- Status: Active
- Owner: Jonathan (@jonathango98)
- Version: 1.2.1
- Last updated: 2026-10-28

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

Use these words the same way in code, copy, issues, and PRs.

| Term | Meaning | See |
|---|---|---|
| Active player | A player with points from anything other than joining. Church scores count only these | GAME-089 |
| Admin | A staff role that runs the game: pause, end sessions, review, fix scores, reset PINs | GAME-110 |
| Anonymous post | A shared takeaway that hides the writer's name from other players. Admins can still see the writer | SAFE-009 |
| Area label | A GitHub label (`area:backend` and so on) that says which part of the app an issue or PR touches | ENG-040 |
| Audit row | A record of who did what, to which record, when, and why | ARCH-050 |
| Auto-unlock | A locked account unlocks itself after 60 minutes | SAFE-022 |
| Blind box | A sealed box with a mystery item, unlocked every 300 points of score. Contents are OPEN | GAME-072, GAME-068 |
| Booth | A staffed table that gives points once per player, for example the mission booth | GAME-041 |
| Check-in | Scanning a session's rotating code on the hall screen before the session starts | GAME-020, GAME-021 |
| Church list | The preloaded list of churches players pick from at sign-up | SAFE-002 |
| Church score | A fair average of points per active player for a church (a shrunk average) | GAME-081, GAME-089 |
| Claimable blind boxes | Blind boxes earned minus blind boxes already claimed, never below 0 | GAME-074 |
| Close redemption | The admin button that ends blind box claims on Sunday when the service starts | GAME-078, GAME-110 |
| Code freeze | Not used. Removed by DEC-053 | ENG-071 |
| Coin | Not used. Coins were replaced by blind box milestones on score | DEC-002 |
| Connection | Two players scanning to meet. Each pair counts once | GAME-013 |
| Feature complete | Late January gate. Nothing new after it | ENG-070 |
| Foundation | The `foundation/` folder and the other protected files. The source of truth | ENG-080 |
| Foundation Change Request (FCR) | A PR that changes a protected file. It merges only with Jonathan's approval | ENG-080 |
| Game booth | The booth where ushers take hidden items and hand out blind boxes | GAME-043, GAME-073 |
| Game director | The person who owns rules, point values, icebreaker questions, prizes, and playtests | 12-team-timeline.md |
| Game state | On, paused, or off | GAME-100 |
| Hidden item | A numbered object placed in a conference area. Turned in at the game booth | GAME-043 |
| Icebreaker | The question both phones show after a connection, for example "Favorite verse?" | GAME-017 |
| Journal | Where a player writes and reads their own takeaways | GAME-030 |
| Last initial | The first letter of a player's last name, shown after the first name on leaderboards | GAME-088 |
| Ledger | The PointLedger table. Score is the sum of its rows for a player | DATA-030 |
| LOCKED | Decided. Build it | README |
| Main screen | The big screen in the ballroom showing leaderboards and the takeaway wall between sessions | UI-040 |
| Milestone | Every 300 points of score, which unlocks one blind box | GAME-070 |
| My Code | A player's personal QR code. It changes every 30 seconds | GAME-001 |
| OPEN | Not decided. Do not build behavior that depends on it | README |
| Open Box | The app screen that shows blind boxes earned, claimed, and claimable, and how to claim | GAME-073 |
| Pause | The game state during sessions. No earning and no claims, except join points at sign-up | GAME-102, GAME-044 |
| Paper fallback | Ushers writing quests on paper when Wi-Fi fails, entered later by an admin | ARCH-081 |
| Player | Anyone who signed up to play | |
| Points service | The one piece of server code that gives or removes points | ARCH-040 |
| PROPOSED | The default to build against. May change after a playtest | README |
| Protected path | A file or folder only Jonathan changes | ENG-080 |
| Real event data | Information about real people or the real venue. Never in the repo | OPS-040 |
| Redemption window | When blind box claims are open: Day 1 evening, Day 2 breaks, and Sunday before the service | GAME-078 |
| Score | A player's total points. Moves the leaderboards and unlocks blind boxes | GAME-003 |
| Screen role | The read-only role for main screen and hall screen devices | ARCH-037 |
| Session | A talk or workshop in the conference program | DATA-014 |
| SQ1 | Version 1 of the QR payload format | ARCH-020 |
| Summary page | Shared takeaways grouped by session, for signed-in players | SAFE-017 |
| Takeaway | A short reflection of at least 15 words written after a session | GAME-030 |
| Takeaway wall | The main screen view of approved shared takeaways | SAFE-018 |
| TOTP | Time-based one-time code. How My Code and check-in codes rotate | ARCH-021 |
| Usher | Game-day volunteer who scans for booths, the photobooth, hidden items, and blind boxes | GAME-112 |
| Visibility | Private, shared with name, or shared anonymously | GAME-031 |
| Wrapped | The personal weekend recap cards that unlock on Sunday | WRAP-001 |
