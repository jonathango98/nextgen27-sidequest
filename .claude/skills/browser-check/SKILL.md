---
name: browser-check
description: Check Side Quest pages in a real browser with Playwright for Python before committing. Use before every commit that changes a route, template, CSS, or JavaScript file (AI-044), and whenever asked to test a screen, check it at 360px, look for browser console errors, take a screenshot for a PR, or write a browser test.
license: Apache-2.0. Adapted from anthropics/skills webapp-testing. Complete terms in LICENSE.txt.
---

# Browser check

Before you commit a change that can affect a page, open every changed screen in a real browser and prove it works (AI-033, AI-044). Never commit on a failed check, and never report a check you did not run.

Rules this skill applies:

- ENG-045: every changed screen works at 360px wide, with no browser console errors.
- ENG-046, AI-042: browser test names include the rule ID.
- ENG-047, SAFE-031: fake data only ("Test Player 1", "Example Church A").
- AI-013: game numbers come from `foundation/game-config.yaml`, even in tests.
- SAFE-030: screenshots, traces, and test databases never go into the repo.

## 1. When to run it

- Before every commit that touches `app/routes/`, `app/templates/`, `app/static/`, or anything a page renders. When unsure, run it.
- When the human asks you to test a screen, take a screenshot, or write a browser test.
- Skip it for changes that cannot affect a page (docs, config comments). Say that you skipped it and why.

## 2. Before you start

1. **App exists?** If there is no `app/` folder or no agreed start command yet, say "No app to check yet" and stop. Do not invent a start command.
2. **Playwright installed?** Run `python -m playwright --version`. If it fails, stop and ask the human before installing anything (AI-046). Playwright is in the stack as PROPOSED (DEC-023). Exact versions are pinned in `pyproject.toml` at kickoff (ENG-057). The install, once approved:

   ```bash
   python -m pip install pytest-playwright
   python -m playwright install chromium webkit
   ```

3. **Fake data only.** Point the app at a fresh test database in the temp folder, seeded with obviously fake players and churches. Never use a copy of real event data.

## 3. Steps

1. **Find the changed screens.** Run `git diff --name-only` and `git diff --name-only --staged`, then match files to routes using the screen inventory in `foundation/06-api-and-screens.md` section 5.
2. **Start the app and run the quick check.** Run the helper's `--help` first. Use it as a black box, without reading its source.

   ```bash
   python .claude/skills/browser-check/scripts/with_server.py \
     --server "<app start command>" --port 8000 \
     -- python .claude/skills/browser-check/examples/check_screen.py http://localhost:8000 /join /login
   ```

   `check_screen.py` opens each path at 360px, fails on console errors, page errors, HTTP errors, or sideways scroll, and saves a full-page screenshot to the temp folder. Copy it into a scratch file and extend it when a screen needs clicks or form input.
3. **Look at every screenshot** with the Read tool. Check that:
   - nothing is cut off and nothing scrolls sideways
   - text is readable and buttons are big enough to tap
   - the paused banner shows when the game is paused (UI-033)
   - only fake data appears
4. **Run the browser tests** in `tests/` with pytest. Send artifacts to the temp folder, because the default `test-results/` folder is inside the repo:

   ```bash
   python -m pytest tests/ --base-url http://localhost:8000 --output "$(python -c 'import tempfile;print(tempfile.gettempdir())')/sidequest-test-results"
   ```

   For My Code, the scanner, and anything camera-related, also run with `--browser webkit`, because many players use iPhone Safari.
5. **Report before committing.** List the screens checked, pass or fail for each, every console error, and the screenshot paths. If anything failed, fix it or stop and ask. If a test fails and you don't understand why, stop and ask (AI-050).

## 4. Writing a browser test

Put browser tests next to the area's other tests (`tests/` mirrors `app/`, ARCH-008). Set the 360px viewport once in `tests/conftest.py`:

```python
import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 360, "height": 740}}
```

Each test uses the `page` fixture from pytest-playwright. Name it with the rule ID:

```python
from playwright.sync_api import Page, expect


def test_safe_002_join_form_asks_only_allowed_fields(page: Page):
    page.goto("/join")
    expect(page.get_by_label("First name")).to_be_visible()
    expect(page.get_by_label("Last name")).to_be_visible()
```

Labels and fields above are examples. Use the real ones from the foundation and the template.

## 5. Pitfalls

- **Don't wait for `networkidle`.** My Code polls `/code/qr` and `/code/incoming` (API-030), and the main screens poll on a timer (API-031). On those pages the network never goes quiet, so `networkidle` makes tests flaky or hang. Use `expect(locator).to_be_visible()` and other `expect` checks, which wait on their own.
- **HTMX swaps the page in place.** After a click, wait for the new content with `expect(...)`, not with `wait_for_timeout`.
- **Use role and label selectors** (`get_by_role`, `get_by_label`, `get_by_text`) before CSS selectors. They match what a player sees and survive template changes.
- **Real camera scanning can't be checked in a headless browser.** Test the page around it, and tell the human the scan itself needs a real phone.
- **Close what you open.** `sync_playwright()` as a context manager and `browser.close()` at the end.

## 6. Credits

Adapted from the `webapp-testing` skill in [anthropics/skills](https://github.com/anthropics/skills) (commit `b9e19e6`), Apache License 2.0, see `LICENSE.txt`. Changes:

- Rewritten for Side Quest: 360px viewport, the polling pages, console error checks, fake data, and this repo's rules.
- `scripts/with_server.py` writes server output to a log file and stops child processes on cleanup.
- The upstream examples are replaced by `examples/check_screen.py`.
