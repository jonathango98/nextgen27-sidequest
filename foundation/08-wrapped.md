# 08 Side Quest Wrapped

- Status: Active (each rule has its own status)
- Owner: Jonathan (@jonathango98)
- Version: 1.0.0
- Last updated: 2026-10-19

> Protected file. AI agents: read only. To propose a change, open a Foundation Change Request issue.

Wrapped is a personal recap of the weekend, like a year-end music recap: short cards you swipe through. It unlocks on Sunday right after results. It only reads data the game already has. It collects nothing new.

## 1. Basics

- **WRAP-001** [LOCKED] Wrapped reads existing data only. It adds no new questions, no new fields, and no tracking.
- **WRAP-002** [LOCKED] An admin unlocks Wrapped on Sunday right after the results. Before that, `/wrapped` shows "Your Wrapped unlocks on Sunday." Config: `wrapped.unlock`.
- **WRAP-003** [LOCKED] No email is collected, so the recap lives in the browser the person played on. A player can also log in on another phone with their PIN (ARCH-032). "Save as image" is the backup.
- **WRAP-004** [LOCKED] Wrapped stays open until the data retention date (SAFE-014). So retention must be at least a few weeks after the event.
- **WRAP-005** [PROPOSED] Effort: about 1 to 2 weeks for one developer. It fits the January build. Playtest 2 ends with a test recap.

## 2. Personal recap cards

`##` means the player's own number.

| Card | Title | Content | Rules |
|---|---|---|---|
| 1 | NextGen 2027 Wrapped | "Hi, [first name]. Here's how your weekend at NextGen went." | |
| 2 | People you met | `##` people from `##` churches and `##` regions, plus your first friend | WRAP-011 |
| 3 | Your collection | `##` favorite verses and `##` favorite foods collected from people you met, plus your top verse | WRAP-012 |
| 4 | Your journal | `##` takeaways from `##` sessions, and a line you wrote | WRAP-013 |
| 5 | Your play style | The Connector, The Explorer, or The Journalist, plus `##` stickers earned | WRAP-014, WRAP-015 |
| 6 | Together we made | `##` connections across `##` churches among `##` players, plus your church's average points | WRAP-016 |

- **WRAP-010** [LOCKED] Six cards, in the order above. The designer sets the final look.
- **WRAP-011** [OPEN] The "`##` regions" number needs region data for each church (DATA-010). Until that is decided, card 2 leaves out regions.
- **WRAP-012** [OPEN] Card 3 depends on who types icebreaker answers (GAME-015, conflict C5), on the question categories (GAME-019), and on how verses are matched (for example "Jn 3:16" and "John 3:16" count as the same verse). Card 3 uses only the player's own pairs (SAFE-006).
- **WRAP-013** [LOCKED] Card 4 may quote any of the player's own takeaways, including private ones, because only that player sees their recap. Private takeaways never appear in anyone else's recap.
- **WRAP-014** [PROPOSED] Play style is the category where most of the player's points came from: Connect is The Connector, Explore is The Explorer, Sessions (check-ins and takeaways) is The Journalist. Manual admin awards do not count toward play style. If two categories tie, the order is OPEN (WRAP-017).
- **WRAP-015** [PROPOSED] "`##` stickers earned" is stickers earned from score (GAME-070), not stickers claimed.
- **WRAP-016** [PROPOSED] Card 6 counts: total connections between different churches, the number of churches with at least one player, and the number of players. "Your church's average points" uses the church score (GAME-081), so it follows the open decision GAME-089.
- **WRAP-017** [OPEN] How a tie between play styles is broken.

## 3. Rules for every card

- **WRAP-031** [LOCKED] Positive only. No low rankings, no "you wrote the fewest takeaways". Spiritual activity is never ranked or compared.
- **WRAP-032** [LOCKED] The "Save as image" file shows only the player's own first name and their own numbers. It never shows other people's names. So the first friend's name (card 2), the top verse text, and the quoted takeaway line are left out of the image.
- **WRAP-033** [OPEN] How the image is made, in the browser or on the server. This is a dependency decision (ARCH-004).

## 4. Other recaps

- **WRAP-020** [LOCKED] A conference recap on the main screen on Sunday, before prizes: total connections, churches connected, takeaways shared, and the most collected verse.
- **WRAP-021** [PROPOSED] "Churches connected" means the number of different church pairs with at least one connection between them. Example: if Example Church A has met B and C, and B has met C, that is 3 pairs.
- **WRAP-022** [LOCKED] The conference recap shows totals only. No individual names.
- **WRAP-030** [OPEN] An optional church recap for each youth pastor: how many from their church played and how many other churches they connected with. This needs a new way for a youth pastor to log in, so it is off until decided. Config: `wrapped.church_recap`.
