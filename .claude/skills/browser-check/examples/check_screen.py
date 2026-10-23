"""Open Side Quest screens at 360px, fail on console errors or sideways scroll, save screenshots.

Usage (with the app already running, or through scripts/with_server.py):
    python check_screen.py http://localhost:8000 /join /login

Exits 1 if any screen has a console error, a page error, or is wider than 360px.
Screenshots go to the temp folder, never into the repo (SAFE-030).
"""

import pathlib
import sys
import tempfile

from playwright.sync_api import expect, sync_playwright

VIEWPORT = {"width": 360, "height": 740}  # ENG-045: every changed screen works at 360px


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    base_url, paths = sys.argv[1].rstrip("/"), sys.argv[2:]
    out_dir = pathlib.Path(tempfile.gettempdir()) / "sidequest-browser-check"
    out_dir.mkdir(exist_ok=True)
    failed = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for path in paths:
            problems = []
            page = browser.new_page(viewport=VIEWPORT)
            page.on("console", lambda m: problems.append(f"console error: {m.text}") if m.type == "error" else None)
            page.on("pageerror", lambda e: problems.append(f"page error: {e}"))

            response = page.goto(base_url + path)
            # No wait for "networkidle": My Code and the main screens poll (API-030, API-031).
            expect(page.locator("body")).to_be_visible()
            if response is not None and response.status >= 400:
                problems.append(f"HTTP {response.status}")

            width = page.evaluate("document.documentElement.scrollWidth")
            if width > VIEWPORT["width"]:
                problems.append(f"page is {width}px wide, so it scrolls sideways at 360px")

            name = path.strip("/").replace("/", "_") or "home"
            shot = out_dir / f"{name}.png"
            page.screenshot(path=str(shot), full_page=True)
            page.close()

            status = "FAIL" if problems else "ok"
            print(f"{status}  {path}  screenshot: {shot}")
            for problem in problems:
                print(f"      {problem}")
            failed = failed or bool(problems)
        browser.close()

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
