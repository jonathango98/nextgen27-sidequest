# 07 Design System

- Status: PROPOSED (everything here may change until the designer signs off)
- Owner: Jonathan (@jonathango98)
- Version: 1.10.0
- Last updated: 2026-11-12

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file says how Side Quest looks, sounds, and feels. The UI designer owns the final look. Until they sign off, build with the tokens below, so a change later only edits one CSS file. The tokens below are the Kairos look (UI-008, DEC-080).

- **UI-001** [PROPOSED] All design tokens live as CSS custom properties in one file, `app/static/css/tokens.css`. Templates and other CSS use the tokens, never raw color or size values.

## 1. Principles

- **UI-002** [PROPOSED] Mobile first. Every screen works at 360px wide with no sideways scrolling. Config: `ui.min_viewport_px`.
- **UI-003** [PROPOSED] Built for one hand. Main actions sit in the lower half of the screen. Every tap target is at least 48px by 48px. Config: `ui.min_tap_target_px`.
- **UI-004** [PROPOSED] Fast on weak hotel Wi-Fi: server-rendered pages, HTMX, very little JavaScript, and small images. The only web fonts are the two brand fonts, Outfit and Inter, self-hosted from `app/static/fonts/` (never a font service), trimmed to Latin and the weights we use, and loaded with `font-display: swap` so text shows at once in the system font. The only brand images are the K mark and one halftone texture in `app/static/img/`. Fonts and images together stay under 120 KB (DEC-080).
- **UI-005** [LOCKED] Meets WCAG 2.1 AA. High contrast that works in a bright lobby and a dim ballroom.
- **UI-006** [PROPOSED] Pear (`--color-accent`) is the one accent. It marks points, the current tab, progress, and connection moments (a new connection, a new church met). Churches have no colors. A church is always shown by its name (DEC-080).
- **UI-008** [PROPOSED] The look is "Kairos", from the Nextgen 2027 brand kit: white paper, black ink, and one Pear accent (`#C1CC52`). Flat: no blur, glass, gradients, or shadows. Every phone page has a black top bar with the white K mark and "Side Quest". The brand halftone texture shows at the edges only, as decoration hidden from screen readers: faintly in the phone top bar, on Home's Pear score panel, and in the main screen corners. It never sits on forms, lists, the scanner, or the QR. Titles, numbers, and buttons use Outfit (a stand-in for the kit's JA Jayagiri Sans). Everything else uses Inter. No flower icons.
- **UI-009** [PROPOSED] The Kairos vibe: bold, clean, and confident, like the conference's printed brand. Big black type on white, Pear where something is earned. Every button is a pill. Buttons are big and few, words are short (UI-057), and nothing competes with the one black main button (UI-035).

## 2. Tokens (PROPOSED)

Contrast ratios below were checked with the WCAG 2.1 formula.

### Color

| Token | Value | Use | Contrast |
|---|---|---|---|
| `--color-bg` | `#FFFFFF` | Page background (phone), also while paused | Text on it: 21:1 |
| `--color-surface` | `#FFFFFF` | Panels, fields, the QR panel | Text on it: 21:1 |
| `--color-text` | `#000000` | Main text | On white: 21:1 |
| `--color-text-muted` | `#5E5E5E` | Secondary text, on white only | On white: 6.48:1 |
| `--color-primary` | `#000000` | Main button and the top bar | White text on it: 21:1 |
| `--color-on-primary` | `#FFFFFF` | Text on black | |
| `--color-on-primary-muted` | `#A3A3A3` | Small text on black | On black: 8.33:1 |
| `--color-accent` | `#C1CC52` | Pear: points pills, the current tab, progress, Home's score panel. A fill only, with black text on it. Never white text on it (1.75:1) | Black text on it: 12.03:1 |
| `--color-on-accent` | `#000000` | Text on Pear | |
| `--color-line` | `#000000` | Outlines of secondary buttons, fields, the bottom bar | 21:1 on white |
| `--color-hairline` | `rgba(0, 0, 0, 0.14)` | Row dividers. Decoration only | |
| `--color-track` | `rgba(0, 0, 0, 0.18)` | The empty part of a progress bar, always with numbers (UI-051) | |
| `--color-success` | `#1E7B3A` | Success messages | On white: 5.32:1 |
| `--color-error` | `#B42318` | Error messages and Log out | On white: 6.57:1 |
| `--color-screen-bg` | `#000000` | Main screen background | |
| `--color-screen-text` | `#FFFFFF` | Main screen text | On black: 21:1 |
| `--color-screen-muted` | `#A3A3A3` | Main screen secondary text | On black: 8.33:1 |
| `--color-screen-accent` | `#C1CC52` | Main screen points and first place | On black: 12.03:1 |

- **UI-007** [REMOVED] Was: church colors from a fixed palette. Churches have no colors now and are shown by name (DEC-080).

### Type and spacing

| Token | Value | Use |
|---|---|---|
| `--font-family` | `"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | Body text, labels, helper text. Self-hosted (UI-004) |
| `--font-family-display` | `"Outfit", "Avenir Next", Futura, system-ui, sans-serif` | Titles (700), numbers (700), and buttons (600). Self-hosted (UI-004) |
| `--font-size-body` | `16px` | Body text on phones (never smaller) |
| `--font-size-small` | `14px` | Labels and helper text only |
| `--font-size-h1` | `40px` | Page titles on phones, lowercase with a period (UI-058) |
| `--font-size-score-hero` | `116px` | The big score on Home |
| `--space-1` to `--space-6` | `4px`, `8px`, `12px`, `16px`, `24px`, `32px` | Padding and gaps |
| `--radius` | `28px` | Panels |
| `--radius-card` | `24px` | Tiles and cards |
| `--radius-pill` | `999px` | Every button and points pill |
| `--radius-field` | `14px` | Text fields and pickers |
| `--border` | `1.5px` | Black outlines of secondary buttons, fields, and panels |
| `--tap-min` | `48px` | Minimum tap target (UI-003) |

## 3. Components

| Component | Notes |
|---|---|
| Button | A pill. Main: filled black with white text, one per screen (UI-035). Secondary: white with a black outline. Outfit 600 label. Full width on phones. At least 48px tall. |
| Card | White with a black outline (`--border`), `--radius-card`, padding `--space-4`. No shadow. |
| Bottom bar | Three tabs, each an icon and a label (UI-030). White with a black top line. The current tab has a Pear pill behind its icon and a bold label. Each tab is at least 60px tall. |
| Points pill | Pear, bold black text, for example "+20". Only for points. |
| Score display | Big number, label "points". |
| Box progress bar | Shows points toward the next blind box, for example "120 / 300". Shows "All 3 boxes unlocked!" at the max. |
| QR panel | Solid white background, large QR, quiet zone kept, screen brightness tip. |
| Scanner frame | Camera view with a square guide and one line of help text. |
| Result message | Success, info, or error, with an icon and text (never color alone). |
| Paused banner | Shown at the top of every player page while paused (UI-033). |
| Visibility picker | Three radio options for takeaways, with the note in UI-031. |
| Leaderboard row | Rank, first name, last initial, church, score (GAME-088). |
| Takeaway card | Text, then first name and church, or "Anonymous". |
| Wrapped card | Full-screen card, swipe or tap to move on (WRAP-010). |

## 4. Phone screens

- **UI-030** [PROPOSED] Every player page has the same frame: a top bar, the content, and a bottom bar with three tabs: Home, My Code, Quests. Only Home shows the score (UI-036). Every other top bar shows just the Side Quest name, which links to Home (DEC-062). Scan is not a tab. It opens from the Scan button on My Code and from Meet friends on Home. The journal list and the shared takeaways page have a "Back to home" link above the title, and Scan has "Back to My Code".
- **UI-031** [LOCKED] The Journal form shows this note next to the visibility choice, in plain words: "Anonymous hides your name from other players. Game organizers can still see who wrote it." (SAFE-009)
- **UI-032** [PROPOSED] If submitting a form fails (paused, no connection, too short), the text stays in the form so nothing typed is lost.
- **UI-033** [PROPOSED] The paused banner says something short like "Game paused". It never scolds. While the game is paused, every player page turns grayscale (`--paused-filter`), so a glance shows nothing can be earned. Staff pages and the main screen keep their color (DEC-080).
- **UI-034** [PROPOSED] The scanner result shows within one second of a scan, with a big clear message: the friend's name and church, then the icebreaker question. Points show after the player types their answer, for example "+15" (GAME-016, DEC-053).
- **UI-035** [PROPOSED] Each screen has at most one main (black) button, for its most important action. Everything else is white with a black outline.
- **UI-036** [PROPOSED] Home layout, top to bottom: the player's first name ("Hi, <first name>"), the big score (`--font-size-score-hero`) with "points" under it, then blind box progress ("Next box" with the numbers, UI-051). In the lower half (UI-003): Meet friends (the black main button, opens the scanner), a row split in two with Write, "A journal" under it (the player's own journal list, which has Write a takeaway on top, with its points pill while the game is on, DEC-077), and Read, "All journals" under it (shared takeaways, `/summary`), then Claim box (Open Box) (DEC-062). The top bar has a settings gear (at least 48px, UI-003) that opens a small menu. Its only item is Log out in red (`--color-error`), which asks "Log out on this phone?" first and signs out this phone only (ARCH-034, DEC-058).
- **UI-037** [PROPOSED] My Code shows the QR panel, then a black Scan button. The scanner, the icebreaker, and the scan result all sit under the My Code tab.
- **UI-038** [PROPOSED] The shared takeaways page (`/summary`) lists approved shared takeaways grouped by session, newest session first, as takeaway cards (section 3).
- **UI-039** [PROPOSED] The Journal form's main button is "Submit" with its points pill. An outlined Cancel button under it goes back to Home without saving (UI-035, DEC-062).

The design mockups show a scan going to the icebreaker first and the points result after it. GAME-016 settles it (DEC-042): each player's points land when they type their own answer, so build this order.

## 5. Main screen

- **UI-040** [LOCKED] While the game is on or paused, the main screen takes turns showing the player leaderboard, the church leaderboard, one approved shared takeaway, and photobooth pictures (API-031, DEC-069, DEC-079). While the game is off, it shows the off view (UI-044). It shows only photobooth photos an admin approved, and never a photo of a minor without consent (SAFE-024, SAFE-038). It never shows a "boxes left" counter (GAME-077).
- **UI-041** [PROPOSED] Readable from the back of a ballroom. At 1920x1080, no text is smaller than 40px, and leaderboard rows are at least 56px tall. Check this from the back of the room at the venue walkthrough (OPS-030). Config: `main_screen.min_text_px_1080p`, `main_screen.min_row_px_1080p`.
- **UI-042** [PROPOSED] The main screen uses the dark screen tokens (white text on black, Pear for points and first place) to reduce glare in a dim room.
- **UI-043** [PROPOSED] No fast animation on the main screen. Views change slowly so people can read them.
- **UI-044** [PROPOSED] While the game is off, the main screen shows either "Side Quest is offline" or the conference recap (WRAP-020). An admin switches between the two on the admin console, and each switch is written in the audit log (DEC-069).

## 6. Copy voice

- **UI-050** [LOCKED] Copy is warm, short, and encouraging. It never shames. It never ranks spiritual activity (takeaways, check-ins, prayer). It fits a youth ministry audience without sounding childish.

| Do | Don't |
|---|---|
| "Nice! You met someone from a new church. +15" | "Only 15 points. Try harder." |
| "Session in progress. See you at the break!" | "You can't play now." |
| "Add 3 more words to save this." | "Your takeaway is too short." |
| "You wrote 4 takeaways this weekend." | "You wrote fewer takeaways than most people." |
| "Keep playing to unlock your next box." | "Not enough points." |

- **UI-057** [PROPOSED] Buttons, labels, and helper lines are one or two words, for example "Meet friends", "Scan again", "Submit +20". Don't explain what the screen already shows. Use longer text only where a rule sets the exact words (UI-031).
- **UI-058** [PROPOSED] Page titles are lowercase and end with a period, like the brand kit, for example "quests." and "join side quest.". A title that is a whole sentence, like "Side Quest is offline.", keeps sentence case. Buttons, labels, and body text stay in sentence case (DEC-080).

## 7. Accessibility

- **UI-051** [LOCKED] Color is never the only way to show meaning. Errors have text, the current tab has a bold label, and the progress bar has numbers.
- **UI-052** [LOCKED] Text contrast is at least 4.5:1 (3:1 for large text and for UI parts like borders and icons).
- **UI-053** [PROPOSED] Every input has a visible label. A form whose only text box sits right under the page title may use that title as the label (`aria-labelledby`), as the Journal form does (DEC-062). Every icon button has an accessible name.
- **UI-054** [PROPOSED] Focus is always visible for keyboard and switch users.
- **UI-055** [PROPOSED] Animations, including Wrapped transitions, respect the "reduce motion" setting.
- **UI-056** [PROPOSED] Pages still work when text is enlarged to 200%.
