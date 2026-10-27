# 07 Design System

- Status: PROPOSED (everything here may change until the designer signs off)
- Owner: Jonathan (@jonathango98)
- Version: 1.4.0
- Last updated: 2026-10-26

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file says how Side Quest looks, sounds, and feels. The sticker and UI designer owns the final look. Until they sign off, build with the tokens below, so a change later only edits one CSS file. The tokens below are the Mix look (UI-008, DEC-035).

- **UI-001** [PROPOSED] All design tokens live as CSS custom properties in one file, `app/static/css/tokens.css`. Templates and other CSS use the tokens, never raw color or size values.

## 1. Principles

- **UI-002** [PROPOSED] Mobile first. Every screen works at 360px wide with no sideways scrolling. Config: `ui.min_viewport_px`.
- **UI-003** [PROPOSED] Built for one hand. Main actions sit in the lower half of the screen. Every tap target is at least 48px by 48px. Config: `ui.min_tap_target_px`.
- **UI-004** [PROPOSED] Fast on weak hotel Wi-Fi: server-rendered pages, HTMX, very little JavaScript, small images, and no web fonts (use the system font stack).
- **UI-005** [LOCKED] Meets WCAG 2.1 AA. High contrast that works in a bright lobby and a dim ballroom.
- **UI-006** [PROPOSED] Visual motif from the leadership deck: each church is a color, and gold lines are friendships across churches. Gold is the accent for connection moments (a new connection, a new church met).
- **UI-008** [PROPOSED] The look is "Mix", a light, overexposed superbloom. The phone background is cream with large blurred streaks of the bloom colors and a light film grain. The streaks are CSS. The grain is one tiny texture generated in the CSS, so there is no image file to download (UI-004). The background is decoration only and hidden from screen readers. Titles, numbers, and buttons use the system serif. Everything else uses the system sans. No flower icons.
- **UI-009** [PROPOSED] The Mix vibe: bright, warm, and calm, like a sunny photo of a flower field taken a little overexposed. Black serif text feels like a printed program. Thin black viewfinder corners frame the top of Home. Buttons are big and few, words are short (UI-057), and nothing competes with the one black main button (UI-035).

## 2. Tokens (PROPOSED)

Contrast ratios below were checked with the WCAG 2.1 formula.

### Color

| Token | Value | Use | Contrast |
|---|---|---|---|
| `--color-bg` | `#FBF4EE` | Cream page background (phone) | Text on it: 15.80:1 |
| `--color-bg-paused` | `#F3F1F0` | Page background while paused, with the bloom streaks faded to gray | Text on it: 15.29:1 |
| `--color-bloom-orange` | `#F6B47B` | Background streaks only | Text on it: 9.62:1 |
| `--color-bloom-marigold` | `#F8C96D` | Background streaks only | Text on it: 11.12:1 |
| `--color-bloom-pink` | `#F4B0C8` | Background streaks only | Text on it: 9.75:1 |
| `--color-bloom-magenta` | `#EFB5CA` | Background streaks only | Text on it: 9.95:1 |
| `--color-bloom-leaf` | `#C4D1B5` | Background streaks only | Text on it: 10.77:1 |
| `--color-bloom-sky` | `#C5D4EB` | Background streaks only | Text on it: 11.47:1 |
| `--color-surface` | `rgba(255, 255, 255, 0.68)` | Frosted glass: cards, secondary buttons, the bottom bar. Used with `--blur-glass` | Text on it: 14.37:1 at worst (over orange) |
| `--color-surface-solid` | `#FFFFFF` | QR panel and text fields | Text on it: 17.22:1 |
| `--color-text` | `#1E1A1C` | Main text | On cream: 15.80:1 |
| `--color-text-muted` | `#5B5458` | Secondary text, on white or glass only | On white: 7.36:1. On glass: 6.14:1 at worst |
| `--color-primary` | `#1E1A1C` | Main button and current tab, filled with a gradient from `#3A3236` to `#1E1A1C` | White text on it: 12.43:1 at the light end |
| `--color-gold` | `#FFC629` | Points pills only | Dark text on it: 10.95:1 |
| `--color-gold-line` | `#A87400` | Gold lines and borders on white | On white: 4.07:1. Lines and large text only, never body text |
| `--color-hairline` | `#EEE8EA` | Row dividers. Decoration only | |
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
| `--font-family` | `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | Body text, labels, helper text |
| `--font-family-display` | `ui-serif, "New York", "Iowan Old Style", Georgia, serif` | Titles, numbers, and buttons. A system font, not a web font (UI-004) |
| `--font-size-body` | `16px` | Body text on phones (never smaller) |
| `--font-size-small` | `14px` | Labels and helper text only |
| `--font-size-h1` | `38px` | Page titles on phones |
| `--font-size-score` | `34px` | The score in the top bar |
| `--font-size-score-hero` | `128px` | The big score on Home (120px for the points on the scan result) |
| `--space-1` to `--space-6` | `4px`, `8px`, `12px`, `16px`, `24px`, `32px` | Padding and gaps |
| `--radius` | `26px` | Cards, panels, and big buttons |
| `--radius-pill` | `999px` | One-line buttons and points pills |
| `--radius-tab` | `18px` | Bottom bar tabs |
| `--blur-glass` | `18px` | Backdrop blur behind `--color-surface` |
| `--tap-min` | `48px` | Minimum tap target (UI-003) |

## 3. Components

| Component | Notes |
|---|---|
| Button | Main: filled black, one per screen (UI-035). Secondary: frosted glass. Serif label. Full width on phones. At least 48px tall. |
| Card | Frosted glass (`--color-surface`, `--blur-glass`), `--radius`, padding `--space-4`, a 1px white top highlight and a soft two-layer shadow. |
| Bottom bar | Three tabs, each an icon and a label (UI-030). The current tab is filled black. Each tab is at least 60px tall. |
| Points pill | Gold, bold dark text, for example "+20". Only for points. |
| Score display | Big number, label "points". |
| Sticker progress bar | Shows points toward the next sticker, for example "120 / 300". Shows "All 3 stickers unlocked!" at the max. |
| QR panel | Solid white background, large QR, quiet zone kept, screen brightness tip. |
| Scanner frame | Camera view with a square guide and one line of help text. |
| Result message | Success, info, or error, with an icon and text (never color alone). |
| Paused banner | Shown at the top of every player page while paused (UI-033). |
| Visibility picker | Three radio options for takeaways, with the note in UI-031. |
| Leaderboard row | Rank, first name, last initial, church, score (GAME-088). |
| Takeaway card | Text, then first name and church, or "Anonymous". |
| Wrapped card | Full-screen card, swipe or tap to move on (WRAP-010). |

## 4. Phone screens

- **UI-030** [PROPOSED] Every player page has the same frame: a top bar with the score, the content, and a bottom bar with three tabs: Home, My Code, Quests. Scan is not a tab. It opens from the Scan button on My Code and from Meet friends on Home. Home shows the big score itself, so its top bar has no score.
- **UI-031** [LOCKED] The Journal form shows this note next to the visibility choice, in plain words: "Anonymous hides your name from other players. Game organizers can still see who wrote it." (SAFE-009)
- **UI-032** [PROPOSED] If submitting a form fails (paused, no connection, too short), the text stays in the form so nothing typed is lost.
- **UI-033** [PROPOSED] The paused banner says something short like "Game paused". It never scolds.
- **UI-034** [PROPOSED] The scanner result shows within one second of a scan, with a big clear message, for example "+15" with the friend's name and church.
- **UI-035** [PROPOSED] Each screen has at most one main (black) button, for its most important action. Everything else is frosted white.
- **UI-036** [PROPOSED] Home layout, top to bottom: the big score (`--font-size-score-hero`) with "points" under it, then sticker progress ("Next sticker" with the numbers, UI-051). In the lower half (UI-003): Meet friends (the black main button, opens the scanner), a row split in two with Write (new journal entry, with its points pill) and Read (shared takeaways, `/summary`), then Redeem box (Open Box).
- **UI-037** [PROPOSED] My Code shows the QR panel, then a black Scan button. The scanner, the icebreaker, and the scan result all sit under the My Code tab.
- **UI-038** [PROPOSED] The shared takeaways page (`/summary`) lists approved shared takeaways grouped by session, newest session first, as takeaway cards (section 3).

The Mix mockup shows a scan going to the icebreaker first and the points result after it. GAME-016 settles it (DEC-042): each player's points land when they type their own answer, so build this order.

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

- **UI-057** [PROPOSED] Buttons, labels, and helper lines are one or two words, for example "Meet friends", "Scan again", "Save +20". Don't explain what the screen already shows. Use longer text only where a rule sets the exact words (UI-031).

## 7. Accessibility

- **UI-051** [LOCKED] Color is never the only way to show meaning. Errors have text, church colors have names, and the progress bar has numbers.
- **UI-052** [LOCKED] Text contrast is at least 4.5:1 (3:1 for large text and for UI parts like borders and icons).
- **UI-053** [PROPOSED] Every input has a visible label. Every icon button has an accessible name.
- **UI-054** [PROPOSED] Focus is always visible for keyboard and switch users.
- **UI-055** [PROPOSED] Animations, including Wrapped transitions, respect the "reduce motion" setting.
- **UI-056** [PROPOSED] Pages still work when text is enlarged to 200%.
