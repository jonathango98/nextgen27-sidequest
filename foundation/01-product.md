# 01 Product

- Status: Active (each rule has its own status)
- Owner: Jonathan (@jonathango98)
- Version: 1.2.0
- Last updated: 2026-10-29

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

## 1. What it is

- **PRD-001** [LOCKED] Side Quest is an optional phone game during NextGen Conference 2027, a conference for youth leaders. Its goal is to help youth leaders meet people from other churches and regions.
- **PRD-002** [LOCKED] Players join by scanning one QR code. It runs in the phone's web browser on iPhone and Android. Nothing to download or install.
- **PRD-003** [LOCKED] Players earn points by meeting people, exploring the venue, and sharing what they learned in sessions. The biggest points come from meeting someone from another church.
- **PRD-004** [LOCKED] Playing is optional. Nobody is required to join, and nothing at the conference depends on playing.

## 2. The problem

At most conferences, youth leaders spend their free time with their own church. Side Quest makes meeting other churches the easiest way to score.

It also supports the program. Small rewards go to attending sessions, visiting the mission booth, and writing takeaways after talks. The game pauses whenever a session runs (GAME-101).

## 3. Goals and success metrics

- **PRD-010** [LOCKED] Success is measured with these metrics:

| Metric | How it is counted |
|---|---|
| Players | Attendees who chose to play |
| Cross-church connections per player | Connections between different churches, divided by players |
| Churches connected | Pairs of churches with at least one connection between them (WRAP-021) |
| Takeaways | Takeaways shared, and how often the summary page is read |
| Feedback | Attendee feedback, and how many leaders want to reuse the ideas at home |

- **PRD-011** [OPEN] Target numbers for each metric. They are set after Playtest 1.

## 4. Audience and event shape

- **PRD-020** [LOCKED] Players: 200 to 300 youth leaders from many churches and regions. Some are under 18 (see `03-safety-privacy.md`).
- **PRD-021** [LOCKED] Where: the conference hotel venue. The venue name is not written in this repo.
- **PRD-022** [PROPOSED] The event runs 5 to 7 March 2027 (DEC-050). Playtest and walkthrough dates follow from this. The data retention date counts from the last day (SAFE-014). Owner: organizers. Config: `event.end_date`.

### The three days

| Day | When | What happens | Game status |
|---|---|---|---|
| Day 1 | Evening | Game intro on stage, everyone scans the join QR together, first connections | On after the intro |
| Day 2 | Full day | Meeting people, booths, hidden items, takeaways after each session | On during breaks, paused during sessions |
| Day 3 | Sunday morning service | Final player and church results, prizes, Wrapped unlocks | Off (blind box claims stay open until the service, GAME-078) |

- **PRD-023** [LOCKED] The three-day shape above (GAME-104).

## 5. Asks from leadership

- **PRD-030** [LOCKED] The game needs leadership approval, 5 to 10 ushers, Wi-Fi for about 300 phones, stage time on all three days, and a budget for the server, hardware, printed materials, and blind boxes. Details and dates are in `12-team-timeline.md`. Budget amounts are not written in this repo.

## 6. Not in v1

- **PRD-040** [LOCKED] These are not part of v1:

| Item | Why | Rule |
|---|---|---|
| Secret words from the stage | Nothing should reward opening a phone during a talk | GAME-051 |
| Secret Pastors | Removed | GAME-051 |
| Selfie prompts | Removed | GAME-051 |
| Midday challenge | On hold (parked design kept) | GAME-120 |
| Golden QR drops | Not confirmed | GAME-121 |
| Coins | Replaced by blind box milestones on score | DEC-002 |
| "Boxes left" counter | Removed | GAME-077 |
| Messaging between players | Safety | SAFE-005 |
| Email or phone collection | Safety | SAFE-003 |
| Photo uploads | Safety | SAFE-025 |
| Points for prayer, encouragement, or reading | Never reward spiritual activity with points | GAME-050 |
| Money of any kind | Safety | SAFE-011 |

## 7. Future potential (not v1)

- **PRD-041** [LOCKED] These are ideas for later. Do not build them in v1:
  - an on-time QR code for arriving before a session starts
  - workshop Q&A from phones
  - live polls during sessions
  - reusing the app for future conferences and camps, including other churches' events
