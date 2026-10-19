# 07 Design System

- Status: PROPOSED (everything here may change until the designer signs off)
- Owner: Jonathan (@jonathango98)
- Version: 1.0.0
- Last updated: 2026-10-19

> Protected file. AI agents: read only. To propose a change, open a Foundation Change Request issue.

This file says how Side Quest looks, sounds, and feels. The sticker and UI designer owns the final look. Until they sign off, build with the tokens below, so a change later only edits one CSS file.

- **UI-001** [PROPOSED] All design tokens live as CSS custom properties in one file, `app/static/css/tokens.css`. Templates and other CSS use the tokens, never raw color or size values.

## 1. Principles

- **UI-002** [PROPOSED] Mobile first. Every screen works at 360px wide with no sideways scrolling. Config: `ui.min_viewport_px`.
- **UI-003** [PROPOSED] Built for one hand. Main actions sit in the lower half of the screen. Every tap target is at least 48px by 48px. Config: `ui.min_tap_target_px`.
- **UI-004** [PROPOSED] Fast on weak hotel Wi-Fi: server-rendered pages, HTMX, very little JavaScript, small images, and no web fonts (use the system font stack).
- **UI-005** [LOCKED] Meets WCAG 2.1 AA. High contrast that works in a bright lobby and a dim ballroom.
- **UI-006** [PROPOSED] Visual motif from the leadership deck: each church is a color, and gold lines are friendships across churches. Gold is the accent for connection moments (a new connection, a new church met).

## 2. Tokens (PROPOSED)

Contrast ratios below were checked with the WCAG 2.1 formula.

### Color

| Token | Value | Use | Contrast |
|---|---|---|---|
| `--color-bg` | `#FFFFFF` | Page background (phone) | |
| `--color-surface` | `#F5F6F8` | Cards | Text on it: 16.86:1 |
| `--color-text` | `#14151A` | Main text | On white: 18.23:1 |
| `--color-text-muted` | `#545A66` | Secondary text | On white: 6.93:1 |
| `--color-primary` | `#1F4FD1` | Primary buttons, links | White text on it: 6.78:1 |
| `--color-gold` | `#F2C14E` | Gold accent fill (badges, connection moments) | Dark text on it: 10.86:1 |
| `--color-gold-line` | `#A87400` | Gold lines and borders on white | On white: 4.07:1. Lines and large text only, never body text |
| `--color-success` | `#1E7B3A` | Success messages | On white: 5.32:1 |
| `--color-error` | `#B42318` | Error messages | On white: 6.57:1 |
| `--color-screen-bg` | `#0E1015` | Main screen background | |
| `--color-screen-text` | `#FFFFFF` | Main screen text | On screen background: 19.03:1 |
| `--color-screen-muted` | `#B3B9C4` | Main screen secondary text | On screen background: 9.65:1 |
| `--color-screen-gold` | `#F2C14E` | Main screen accent | On screen background: 11.34:1 |

- **UI-007** [PROPOSED] Church colors come from a fixed palette that repeats when there are more churches than colors. The church name is always shown next to its color. Color alone never carries meaning (UI-051).

### Type and spacing

| Token | Value | Use |
|---|---|---|
| `--font-family` | `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | All text |
| `--font-size-body` | `16px` | Body text on phones (never smaller) |
| `--font-size-small` | `14px` | Labels and helper text only |
| `--font-size-h1` | `28px` | Page titles on phones |
| `--font-size-score` | `40px` | The score number |
| `--space-1` to `--space-6` | `4px`, `8px`, `12px`, `16px`, `24px`, `32px` | Padding and gaps |
| `--radius` | `12px` | Cards and buttons |
| `--tap-min` | `48px` | Minimum tap target (UI-003) |

## 3. Components

| Component | Notes |
|---|---|
| Button | Primary (filled) and secondary (outlined). Full width on phones. At least 48px tall. |
| Card | Surface color, radius, padding `--space-4`. |
| Score display | Big number, label "points". |
| Sticker progress bar | Shows points toward the next sticker, for example "120 / 300". Shows "All 3 stickers unlocked!" at the max. |
| QR panel | White background, large QR, quiet zone kept, screen brightness tip. |
| Scanner frame | Camera view with a square guide and one line of help text. |
| Result message | Success, info, or error, with an icon and text (never color alone). |
| Paused banner | Shown at the top of every player page while paused (UI-033). |
| Visibility picker | Three radio options for takeaways, with the note in UI-031. |
| Leaderboard row | Rank, first name, church, score. |
| Takeaway card | Text, then first name and church, or "Anonymous". |
| Wrapped card | Full-screen card, swipe or tap to move on (WRAP-010). |

## 4. Phone screens

- **UI-030** [PROPOSED] Every player page has the same frame: a top bar with the score, the content, and a bottom bar with three big buttons: My Code, Scan, Quests.
- **UI-031** [LOCKED] The Journal form shows this note next to the visibility choice, in plain words: "Anonymous hides your name from other players. Game organizers can still see who wrote it." (SAFE-009)
- **UI-032** [PROPOSED] If submitting a form fails (paused, no connection, too short), the text stays in the form so nothing typed is lost.
- **UI-033** [PROPOSED] The paused banner says something like: "Session in progress. The game is paused, see you at the break!" It never scolds.
- **UI-034** [PROPOSED] The scanner result shows within one second of a scan, with a big clear message, for example "Connected with Test Player 2 from Example Church B! +15".

## 5. Main screen

- **UI-040** [LOCKED] The main screen shows leaderboards and the takeaway wall only between sessions. While the game is paused, it shows a neutral holding screen with no leaderboard. It never shows a photo of a minor without consent (SAFE-024). It never shows a "boxes left" counter (GAME-077).
- **UI-041** [PROPOSED] Readable from the back of a ballroom. At 1920x1080, no text is smaller than 40px, and leaderboard rows are at least 56px tall. Check this from the back of the room at the venue walkthrough (OPS-030). Config: `main_screen.min_text_px_1080p`, `main_screen.min_row_px_1080p`.
- **UI-042** [PROPOSED] The main screen uses the dark screen tokens (white text on near-black) to reduce glare in a dim room.
- **UI-043** [PROPOSED] No fast animation on the main screen. Views change slowly so people can read them.

## 6. Copy voice

- **UI-050** [LOCKED] Copy is warm, short, and encouraging. It never shames. It never ranks spiritual activity (takeaways, check-ins, prayer). It fits a youth ministry audience without sounding childish.

| Do | Don't |
|---|---|
| "Nice! You met someone from a new church. +15" | "Only 15 points. Try harder." |
| "Session in progress. See you at the break!" | "You can't play now." |
| "Add 3 more words to save this." | "Your takeaway is too short." |
| "You wrote 4 takeaways this weekend." | "You wrote fewer takeaways than most people." |
| "Keep playing to unlock your next sticker." | "Not enough points." |

## 7. Accessibility

- **UI-051** [LOCKED] Color is never the only way to show meaning. Errors have text, church colors have names, and the progress bar has numbers.
- **UI-052** [LOCKED] Text contrast is at least 4.5:1 (3:1 for large text and for UI parts like borders and icons).
- **UI-053** [PROPOSED] Every input has a visible label. Every icon button has an accessible name.
- **UI-054** [PROPOSED] Focus is always visible for keyboard and switch users.
- **UI-055** [PROPOSED] Animations, including Wrapped transitions, respect the "reduce motion" setting.
- **UI-056** [PROPOSED] Pages still work when text is enlarged to 200%.
