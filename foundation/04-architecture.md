# 04 Architecture

- Status: Active (each rule has its own status)
- Owner: Jonathan (@jonathango98)
- Version: 1.4.0
- Last updated: 2026-10-23

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file says how Side Quest is built and run. The stack is PROPOSED and the developers confirm it at kickoff (mid-November). The security rules are LOCKED no matter which stack is chosen.

## 1. Stack

- **ARCH-001** [PROPOSED] The stack is: Python, FastAPI, Jinja2 templates, HTMX, SQLite in WAL mode, all in one Railway service (ARCH-010). Pages are rendered on the server. JavaScript is kept to a minimum.
- **ARCH-002** [LOCKED] Use the allowed stack below. A new library is fine: ask your human first (AI-050), say why in the PR, and pin the version (ENG-057). A new service or piece of infrastructure needs an issue that explicitly approves it (AI-021).
- **ARCH-003** [PROPOSED] Python 3.14. Dependencies are listed in `pyproject.toml` and locked with pip-tools (`pip-compile`) into pinned `requirements*.txt` files (DEC-027).
- **ARCH-004** [PROPOSED] Extra libraries (DEC-027). Pin each version (ENG-057):
  - YAML loader for `game-config.yaml`: PyYAML, with `yaml.safe_load` only
  - server-side QR image generator: segno (no dependencies, SVG output)
  - JavaScript QR decoder for the in-app scanner: `barcode-detector`. It uses the browser's built-in barcode detector where Chromium has one, and ZXing WebAssembly elsewhere, including iPhone Safari. It must work in Safari and Chromium. The script and `.wasm` file are served from our own server, not a CDN
  - the Wrapped "Save as image" file: still OPEN (WRAP-033)

Allowed stack (v1):

| Part | Allowed | Status |
|---|---|---|
| Language | Python 3.14 (ARCH-003) | PROPOSED |
| Web framework | FastAPI, with Uvicorn as the app server | PROPOSED |
| Templates | Jinja2, with autoescape on | PROPOSED |
| Front end | HTMX, plain CSS, small plain JavaScript files | PROPOSED |
| Database | SQLite, WAL mode | PROPOSED |
| Web server and TLS | Railway (HTTPS at its edge). The app serves its own static files | PROPOSED |
| Tests | pytest | PROPOSED |
| Browser tests | Playwright for Python, through pytest-playwright (Chromium and WebKit). Dev and test only, never on the server (DEC-023) | PROPOSED |
| Lint and format | ruff | PROPOSED |
| Hosting | Railway, US West: one production and one staging environment (ARCH-014) | PROPOSED |

## 2. One repo (LOCKED)

- **ARCH-005** [LOCKED] Server and front end live in this one repo. Pages are rendered on the server, so a template and the route that renders it change together in one PR. Work is split by folder and area label, not by repo (decision DEC-001, conflict C7).
- **ARCH-006** [LOCKED] A split into separate repos is reconsidered only if the front end moves to a separate JavaScript app that talks to a JSON API.
- **ARCH-007** [LOCKED] Real event data never lives in the repo: the hidden item list and locations, the usher roster, attendee exports, and playtest data. See OPS-040.

### Proposed app layout

- **ARCH-008** [PROPOSED] The developers confirm this layout at kickoff. Until the `app/` folder exists, CODEOWNERS entries for these paths are PROPOSED too.

| Path | What goes there | Area label | Developer role |
|---|---|---|---|
| `app/main.py` | App factory, middleware | `area:backend` | Backend |
| `app/config.py` | Loads `foundation/game-config.yaml` and environment variables | `area:backend` | Backend |
| `app/routes/player/` | Player routes | `area:player-app` | Player app |
| `app/routes/usher/` | Usher routes | `area:admin-screens` | Admin and screens |
| `app/routes/admin/` | Admin routes | `area:admin-screens` (plus `safety-review`) | Admin and screens |
| `app/routes/screen/` | Main screen routes | `area:admin-screens` | Admin and screens |
| `app/services/` | Points service, QR and TOTP, pause, stickers, Wrapped | `area:backend` | Backend |
| `app/auth/` | Sign-up, PIN, roles, lockout | `area:backend` (plus `safety-review`) | Backend |
| `app/models/` | Database models | `area:backend` (plus `safety-review`) | Backend |
| `migrations/` | Numbered SQL migrations (ENG-050) | `area:backend` (plus `safety-review`) | Backend |
| `app/templates/player/` | Player pages, with `partials/` for HTMX fragments | `area:player-app` | Player app |
| `app/templates/usher/`, `app/templates/admin/`, `app/templates/screen/` | Usher, admin, and main screen pages, each with `partials/` | `area:admin-screens` | Admin and screens |
| `app/templates/partials/` | Shared fragments (paused banner, errors) | `area:player-app` | Player app |
| `app/static/css/` | Stylesheets and design tokens | `area:design` | Designer with player app |
| `app/static/js/` | Small scripts (scanner, polling helpers) | `area:player-app` | Player app |
| `app/static/icons/` | Icons and images | `area:design` | Designer |
| `tests/` | Tests, same folder shape as `app/` | Same as the code under test | Same as the code under test |

## 3. Deployment

- **ARCH-010** [PROPOSED] Production is one Railway service running the app with Uvicorn, as a single replica. Railway terminates HTTPS and forwards requests to the app, which also serves the static files (CSS, JS, the scanner `.wasm`). The SQLite database file sits on a Railway volume mounted to that service. A service with a volume cannot run more than one replica.
- **ARCH-011** [PROPOSED] A staging environment in the same Railway project matches production, with its own volume and fake data only. Every change is tested on staging before production.
- **ARCH-012** [LOCKED] Every page is served over HTTPS. The in-app scanner needs camera access, and browsers only allow that on HTTPS.
- **ARCH-013** [PROPOSED] SQLite allows one writer at a time. Start with a single app process. If a load test (ARCH-071) shows that is too slow, try a small number of workers with a busy timeout. Developers confirm with measurements.
- **ARCH-014** [PROPOSED] Railway is the only host, in the US West region (DEC-028). No separate static host. Costs are not written in this repo.
- **ARCH-015** [LOCKED] The server stores all times in UTC. "Per day" limits use the venue timezone (GAME-105).
- **ARCH-016** [PROPOSED] Railway does not run two deployments on one volume, so every production deploy has a short gap. No production deploys during live game hours.

```
Phone browser ──HTTPS──> Railway edge (TLS) ──> FastAPI app (Uvicorn, static files) ──> SQLite file (WAL, Railway volume)
Main screen browser ──HTTPS──┘
```

## 4. QR codes: SQ1 format (PROPOSED, for developer review)

- **ARCH-020** [PROPOSED] Every QR code the in-app scanner reads holds a plain text payload in this format:

```
SQ1.<kind>.<public_id>.<code>
```

| Part | Meaning | Example |
|---|---|---|
| `SQ1` | Format version. A future format would be `SQ2`. The server refuses versions it does not know. | `SQ1` |
| `kind` | `P` = a player's My Code. `S` = a session check-in code. | `P` |
| `public_id` | A random, opaque ID for the player or session. Never a database row number, never a name. | `k3x9q2mf` |
| `code` | The current rotating code (ARCH-021) | `482913` |

Example payload (fake): `SQ1.P.k3x9q2mf.482913`

- **ARCH-021** [PROPOSED] The rotating code is a time-based one-time code (TOTP, the same idea as an authenticator app). It changes every 30 seconds (GAME-001) and has 6 digits. Config: `qr.code_digits`, `qr.rotation_seconds`.
- **ARCH-022** [PROPOSED] The server accepts the code for the current 30 second window and the one before it, so a small clock difference does not fail a fair scan. Anything older is refused with `CODE_EXPIRED`. Config: `qr.accepted_previous_steps`.
- **ARCH-023** [LOCKED] Codes are made from a secret that lives only on the server, in the environment variable `SQ_QR_SIGNING_KEY`. Each player and session gets its own secret, derived on the server from that key and its public ID. Without the server key, a code cannot be forged, even by someone who has read all the source.
- **ARCH-024** [PROPOSED] The join QR code (shown on stage on Day 1) is a plain HTTPS link to the sign-up page. It carries no secret and earns nothing by itself.
- **ARCH-025** [PROPOSED] The in-app scanner accepts only `SQ1` payloads. Anything else shows "This isn't a Side Quest code."
- **ARCH-026** [LOCKED] A valid code is not enough. The server still checks every rule (pair once, once per session, caps, pause) before it gives points.

## 5. Accounts, login, and roles

- **ARCH-030** [PROPOSED] PINs are stored only as a salted, slow hash. Python's built-in `hashlib.scrypt` is suggested because it needs no new dependency. Developers set the parameters, and the PR goes through safety review (SAFE-016).
- **ARCH-031** [OPEN] Rate limits on login and sign-up per IP address, on top of the per-account lockout (SAFE-022). A 4-digit PIN has only 10,000 values, so without this an attacker can try one common PIN against every account. Config: `auth.ip_rate_limit`.
- **ARCH-032** [LOCKED] To log in on another phone, a player enters their full name, picks their church, and enters their PIN.
- **ARCH-033** [OPEN] What happens when two players from the same church have the same full name (how sign-up and login tell them apart).
- **ARCH-034** [PROPOSED] After login, the server sets a signed session cookie: `Secure`, `HttpOnly`, `SameSite=Lax`. The signing key comes from the environment variable `SQ_SESSION_KEY`. The cookie lasts at least until Wrapped closes (WRAP-004), so the recap stays in the browser the person played on.
- **ARCH-035** [LOCKED] There are four roles: player, usher, admin, and screen. Every usher, admin, and screen route checks the role on the server. Hiding a button is not a security check.
- **ARCH-036** [PROPOSED] Usher and admin accounts are personal (one per person, no shared logins). An admin creates them. They log in with a password, not a 4-digit PIN. The first admin account is created with a server command that reads its password from an environment variable.
- **ARCH-037** [PROPOSED] A main screen device is signed in by an admin and switched to screen mode. A screen session can only read the views meant for the main screen.
- **ARCH-038** [LOCKED] Every request that changes data (POST) is protected against cross-site request forgery. The mechanism is PROPOSED: a token in each form and in an HTMX request header.

## 6. Points service and pause

- **ARCH-040** [LOCKED] All point awards go through one points service. For every award it checks, in one database transaction: the game state, the limits and caps, and duplicates. Then it writes the points ledger row (DATA-030) and an audit row (ARCH-050).
- **ARCH-041** [LOCKED] When the game is paused, the points service refuses the award and the route returns HTTP 423 with the error code `PAUSED` (API-020).
- **ARCH-042** [PROPOSED] Pause takes effect for every request that arrives after the admin switches it. A request that was already saving when pause was switched finishes normally.
- **ARCH-043** [LOCKED] Game numbers come from `game-config.yaml` through `app/config.py`. Code never hardcodes them.

## 7. Logging, audit, and backups

- **ARCH-050** [LOCKED] Every award, revocation, and admin or usher action writes an audit row: who did it, what they did, to which record, the reason (if any), and when.
- **ARCH-051** [LOCKED] Logs never contain PINs, icebreaker answers, takeaway text, last names, or session cookies. Logs refer to players by internal ID.
- **ARCH-052** [LOCKED] Logs, database files, and backups stay on the server. They are never committed (SAFE-030). They are deleted on the retention date (SAFE-014).
- **ARCH-053** [OPEN] Backup frequency and whether an encrypted copy is kept off Railway. Railway volume backups restore only into the same project and environment, so they do not count as the off-Railway copy. Developers propose this before Playtest 2.

## 8. Performance and the join moment

- **ARCH-070** [PROPOSED] Target: 95% of requests finish in under 500 ms, measured on the production setup.
- **ARCH-071** [LOCKED] About 300 phones join at once during the Day 1 stage intro. This moment is load tested on staging before Playtest 2 and on the venue Wi-Fi at the mid-February walkthrough (OPS-030).
- **ARCH-072** [OPEN] The exact load test profile (how many sign-ups in how many seconds). Developers propose it before the load test.
- **ARCH-073** [PROPOSED] The sign-up page is as small as possible: server-rendered HTML, no web fonts, no images beyond a logo, and static files sent with long cache headers.
- **ARCH-074** [PROPOSED] v1 uses HTMX polling for live updates (My Code refresh, the second phone in a connection, main screen views). No WebSockets. Polling intervals live in config.

## 9. When the Wi-Fi fails

Weak or overloaded Wi-Fi is the biggest risk (see `11-operations-runbook.md`).

- **ARCH-080** [PROPOSED] If the server cannot be reached, the phone shows a clear "No connection, try again" message. The phone does not queue earning actions to send later, because queued scans would arrive with old codes and confuse scan order.
- **ARCH-081** [PROPOSED] Paper fallback: ushers write the player's full name, church, and the quest on a paper log. Later, an admin enters each line as a manual award with the reason "paper fallback" (GAME-111).
- **ARCH-082** [PROPOSED] Form text is kept in the page when a submit fails, so a player does not lose a takeaway they typed (UI-032).
- **ARCH-083** [PROPOSED] The main screen keeps showing its last loaded view and adds a small "Reconnecting" note.

## 10. Threat model

- **ARCH-060** [LOCKED] Assume every attacker has read all the source code in this repo. Security depends only on server-side secrets, server-side checks, and authenticated roles. Never on hidden code.

| Threat | Example | Defense | Rules |
|---|---|---|---|
| Shared My Code screenshot | A player sends their code to a friend in another room | Code rotates every 30 s; old codes refused | GAME-001, ARCH-022 |
| Forged QR code | Someone builds a valid-looking `SQ1` payload | Codes come from a server-only secret | ARCH-023 |
| Client-side cheating | Someone edits the page or sends their own requests | The server decides all points and checks every rule | GAME-002, ARCH-026, ARCH-040 |
| Duplicate or replayed awards | The same scan sent twice | Database unique constraints plus the points service | DATA-020 to DATA-027 |
| PIN guessing on one account | 10,000 tries on one player | Lockout after 5 wrong tries | SAFE-022 |
| PIN spraying | One PIN tried on every account | IP rate limits | ARCH-031 |
| Fake accounts farming points | One person with two browsers makes accounts in other churches and scans them | Sign-up rate limits, an admin view of unusual activity, prizes claimed in person | ARCH-031, ARCH-062, GAME-090 |
| Role escalation | A player opens an admin URL | Role checked on the server for every route | ARCH-035 |
| Cross-site request forgery | A page tricks a logged-in admin's browser into a POST | CSRF tokens | ARCH-038 |
| Script injection | A takeaway containing HTML or script | Jinja2 autoescape on; user text is never marked safe | ARCH-061 |
| Guessing IDs | Walking through player IDs one by one | Random public IDs, role checks | ARCH-020 |
| Scraping takeaways | Reading the summary page from outside | Summary page needs login | SAFE-017 |
| Leaked secret | A key committed to the repo | Push protection, rotate the key, never rely on secrecy of code | SAFE-030, SAFE-034 |
| Stolen main screen session | Someone uses the screen device | Screen role is read-only | ARCH-037 |

- **ARCH-061** [LOCKED] Jinja2 autoescape stays on. User-written text (names, answers, takeaways) is never marked as safe HTML.
- **ARCH-062** [PROPOSED] The admin console has a view of unusual activity, for example a player with many connections in a short time, so admins can look before prizes are given.
