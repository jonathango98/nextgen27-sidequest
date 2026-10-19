# 06 Routes and Screens

- Status: PROPOSED (developers confirm at kickoff)
- Owner: Jonathan (@jonathango98)
- Version: 1.0.0
- Last updated: 2026-10-19

> Protected file. AI agents: read only. To propose a change, open a Foundation Change Request issue.

This file lists every route, how HTMX is used, the error codes, and every screen. Paths are PROPOSED.

- **API-001** [LOCKED] A route that is not in this file needs an approved issue first. Agents stop and ask before adding one (AI-050).

## 1. HTMX conventions

- **API-002** [PROPOSED] A normal browser request gets a full page. A request with the `HX-Request` header gets only the fragment (partial) it needs.
- **API-003** [PROPOSED] Partials live in `app/templates/<role>/partials/`. Shared partials, such as the paused banner and error messages, live in `app/templates/partials/`.
- **API-004** [LOCKED] Every POST carries a CSRF token (ARCH-038). With HTMX, the token is sent in a request header set once on the page.
- **API-005** [PROPOSED] Errors return the right HTTP status and a small HTML error partial with a friendly message. The error code (section 3) is included in the partial as a data attribute so tests can check it.
- **API-006** [PROPOSED] By default, HTMX does not swap in responses with 4xx or 5xx status codes. Configure HTMX so error partials are shown. Check the docs for the HTMX version you install, because this setting has changed between versions.
- **API-007** [PROPOSED] Pages work without JavaScript where possible (plain forms that submit and reload). The scanner is the main exception.

## 2. Routes

### Player

| Method | Path | What it does | Rules |
|---|---|---|---|
| GET | `/join` | Sign-up form | SAFE-002 |
| POST | `/join` | Create the player, log them in, give join points | GAME-040, GAME-044 |
| GET | `/login` | Login form: full name, church, PIN | ARCH-032 |
| POST | `/login` | Check the PIN, count wrong tries, lock after 5 | SAFE-022 |
| POST | `/logout` | End the session | |
| GET | `/` | Home: score, sticker progress, quests, game state | GAME-070 |
| GET | `/code` | My Code page | GAME-001 |
| GET | `/code/qr` | Partial: the current QR, refreshed by polling | ARCH-074 |
| GET | `/code/incoming` | Partial: tells the scanned player's phone that a connection started | API-032 |
| GET | `/scan` | Scanner page | ARCH-025 |
| POST | `/scan` | Submit a scanned payload (My Code or session check-in) | GAME-014, GAME-020 |
| GET | `/connections/{id}` | Icebreaker question for this pair | GAME-017 |
| POST | `/connections/{id}/answer` | Save an icebreaker answer | GAME-015 |
| GET | `/quests` | Quest list with progress | |
| GET | `/journal` | My takeaways | |
| GET | `/journal/new` | Takeaway form for an ended session | GAME-036 |
| POST | `/journal` | Submit a takeaway | GAME-030, GAME-033 |
| GET | `/summary` | Shared takeaways grouped by session (signed-in only) | SAFE-017 |
| GET | `/stickers` | Open Box: stickers earned, claimed, claimable, how to claim | GAME-073 |
| GET | `/wrapped` | Wrapped cards (after unlock) | WRAP-002 |

### Usher

| Method | Path | What it does | Rules |
|---|---|---|---|
| GET | `/usher` | Usher console | |
| POST | `/usher/booth` | Scan My Code for a booth visit | GAME-041 |
| POST | `/usher/photobooth` | Scan My Code for a photobooth visit | GAME-042 |
| POST | `/usher/hidden-item` | Record an item number and scan My Code | GAME-043 |
| POST | `/usher/sticker-claim` | Scan My Code and record a sticker handed over | GAME-073 |
| GET | `/usher/players` | Look up a player by name (dead phone) | GAME-113 |

### Admin

| Method | Path | What it does | Rules |
|---|---|---|---|
| GET | `/admin` | Admin console: game state, alerts | |
| POST | `/admin/game-state` | Set on, paused, or off | GAME-100, GAME-101 |
| POST | `/admin/sessions/{id}/end` | End a session: open check-in and resume | GAME-026 |
| POST | `/admin/sessions/{id}/close-checkin` | Close check-in | GAME-024 |
| GET | `/admin/review` | Review queue for shared takeaways | SAFE-007 |
| POST | `/admin/review/{id}` | Approve, reject, or hide | SAFE-040, SAFE-041 |
| GET | `/admin/players` | Find players, see scores | |
| POST | `/admin/players/{id}/award` | Manual award with a reason | GAME-111 |
| POST | `/admin/players/{id}/revoke` | Manual revocation with a reason | GAME-111, GAME-114 |
| POST | `/admin/players/{id}/reset-pin` | Unlock and reset a PIN | SAFE-023 |
| POST | `/admin/players/{id}/church` | Fix a player's church | DATA-012 |
| GET, POST | `/admin/churches` | Manage the church list | SAFE-002 |
| GET, POST | `/admin/booths` | Manage booths | GAME-041 |
| GET, POST | `/admin/hidden-items` | Manage item numbers (no locations) | SAFE-010 |
| GET, POST | `/admin/sessions` | Manage sessions (titles only) | DATA-014 |
| GET, POST | `/admin/staff` | Manage usher and admin accounts | ARCH-036 |
| GET | `/admin/activity` | Unusual activity view | ARCH-062 |
| GET | `/admin/audit` | Audit log | ARCH-050 |
| POST | `/admin/wrapped/unlock` | Unlock Wrapped | WRAP-002 |
| POST | `/admin/screen-mode` | Switch this device to screen mode | ARCH-037 |

### Main screen

| Method | Path | What it does | Rules |
|---|---|---|---|
| GET | `/screen` | Main screen: rotates between the views below when the game is on | UI-040 |
| GET | `/screen/players` | Partial: player leaderboard | GAME-086 |
| GET | `/screen/churches` | Partial: church leaderboard | GAME-081 |
| GET | `/screen/takeaways` | Partial: takeaway wall | SAFE-018 |
| GET | `/screen/checkin/{session_id}` | Rotating session check-in QR for the hall screen | GAME-020 |
| GET | `/screen/recap` | Conference recap on Sunday | WRAP-020 |

## 3. Error codes

| HTTP status | Error code | When | Example message |
|---|---|---|---|
| 400 | `BAD_INPUT` | A form field is missing or wrong | "Please pick your church." |
| 400 | `NOT_A_CODE` | The scanned payload is not `SQ1` | "This isn't a Side Quest code." |
| 400 | `TOO_SHORT` | A takeaway has fewer than 15 words | "Add 3 more words to save this." |
| 401 | `LOGIN_REQUIRED` | Not logged in | "Please log in first." |
| 403 | `WRONG_ROLE` | Logged in, but not allowed | "This page is for game staff." |
| 403 | `PIN_LOCKED` | Too many wrong PINs | "This account is locked. Please find an admin at the game booth." |
| 404 | `NOT_FOUND` | No such record | "We couldn't find that." |
| 409 | `ALREADY_CONNECTED` | The pair already exists | "You two are already connected!" |
| 409 | `ALREADY_DONE` | Once-only quest already done | "You already checked in to this session." |
| 409 | `ITEM_CLAIMED` | Hidden item already claimed | "This item was already turned in." |
| 409 | `LIMIT_REACHED` | A daily or total cap is reached | "That's all the photobooth points for today." |
| 409 | `NOTHING_TO_CLAIM` | No claimable stickers | "Keep playing to unlock your next sticker." |
| 409 | `OUT_OF_STOCK` | No packs left | "All the sticker packs are gone." |
| 410 | `CODE_EXPIRED` | The rotating code is too old | "That code expired. Ask them to show it again." |
| 423 | `PAUSED` | The game is paused | "The game is paused during the session." |
| 423 | `GAME_OFF` | The game is off | "The game is closed right now." |
| 429 | `RATE_LIMITED` | Too many tries from one place | "Too many tries. Wait a minute and try again." |

- **API-020** [LOCKED] While the game is paused, every earning action returns HTTP 423 with `PAUSED` (ARCH-041, GAME-102). While it is off, the same actions return 423 with `GAME_OFF` (GAME-108). 423 is used only for these two cases.
- **API-021** [PROPOSED] The other codes in the table above. A PIN lockout uses 403 `PIN_LOCKED`, not 423, so 423 always means "the game is not on".

## 4. Live updates

- **API-030** [PROPOSED] The My Code page polls `/code/qr` so the code changes on time, and polls `/code/incoming` so the scanned player sees the icebreaker without doing anything.
- **API-031** [OPEN] How often main screen views refresh. Config: `main_screen.poll_seconds`.
- **API-032** [PROPOSED] When player A scans player B, B's phone learns about it the next time `/code/incoming` is polled, then shows the same icebreaker question.

## 5. Screen inventory

| Screen | Role | Route | Notes | Rules |
|---|---|---|---|---|
| Join | Player | `/join` | First name, last name, church list, under-18 question, PIN | SAFE-002 |
| PIN set | Player | `/join` (last step) | Enter PIN twice | SAFE-021 |
| Log in | Player | `/login` | Full name, church, PIN | ARCH-032 |
| Home | Player | `/` | Score, sticker progress bar, quick links | GAME-070 |
| My Code | Player | `/code` | Rotating QR, big and bright | GAME-001 |
| Scanner | Player | `/scan` | Camera view, clear result | ARCH-025 |
| Icebreaker | Player | `/connections/{id}` | Same question on both phones | GAME-017 |
| Quests | Player | `/quests` | What earns points and what is done | |
| Journal | Player | `/journal`, `/journal/new` | Visibility choice and the note about anonymous posts | GAME-031, SAFE-009, UI-031 |
| Summary page | Player | `/summary` | Shared takeaways by session | SAFE-017 |
| Open Box | Player | `/stickers` | Earned, claimed, claimable, "Go to the game booth during a break" | GAME-073 |
| Paused state | Player | Banner on every page | Friendly, short, no shaming | UI-033 |
| Wrapped cards | Player | `/wrapped` | Six swipeable cards, Save as image | WRAP-010 |
| Usher console | Usher | `/usher` | Big buttons for each scan type | GAME-112 |
| Admin console | Admin | `/admin` | Game state switch first, then queues | GAME-110 |
| Main screen: leaderboards | Screen | `/screen/players`, `/screen/churches` | Readable from the back of the room | UI-041 |
| Main screen: takeaway wall | Screen | `/screen/takeaways` | Approved shared posts only | SAFE-018 |
| Main screen: check-in QR | Screen | `/screen/checkin/{id}` | Shown in the hall after the session ends | GAME-020 |
| Main screen: paused | Screen | `/screen` | Neutral holding screen, no leaderboard | UI-040 |
| Main screen: conference recap | Screen | `/screen/recap` | Sunday before prizes | WRAP-020 |
