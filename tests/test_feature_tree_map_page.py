"""The Pages feature tree map works out status live from main and open PRs (ENG-107, ENG-108)."""

import json
import re

import pytest
from playwright.sync_api import Page, expect

from scripts import feature_tree_map as ftm

SHA = "a" * 40
HEAD_SHA = "b" * 40
FORK = "example-volunteer/nextgen27-sidequest"
RAW = "https://raw.githubusercontent.com/"
MAIN_README = "### Working\n\n### In progress\n\n### Planned\n"
MAIN_DECISIONS = "## 3. Open decisions\n\n## 4. Resolved\n"
CORS = {"Access-Control-Allow-Origin": "*"}


@pytest.fixture
def map_page(tmp_path):
    """The map built with nothing Working but the already-built pieces, and no OPEN rules."""
    tree, _, _ = ftm.load()
    status = ftm.statuses(tree, MAIN_README, {})
    path = tmp_path / "index.html"
    path.write_text(ftm.render_html(tree, status, {}, "test123"))
    ready = sorted(i for i, s in status.items() if s == "ready")
    return path.as_uri(), tree, ready


def fake_github(page, main_readme, pr_readme, api_status=200):
    def api(route):
        if api_status != 200:
            return route.fulfill(status=api_status, headers=CORS, body="{}")
        url = route.request.url
        if url.endswith("/commits/main"):
            body = {"sha": SHA}
        else:
            body = [
                {"number": 7, "head": {"repo": {"full_name": FORK}, "sha": HEAD_SHA}}
            ]
        route.fulfill(
            headers=CORS, content_type="application/json", body=json.dumps(body)
        )

    files = {
        f"{ftm.REPO}/{SHA}/README.md": main_readme,
        f"{ftm.REPO}/{SHA}/foundation/13-decisions.md": MAIN_DECISIONS,
        f"{FORK}/{HEAD_SHA}/README.md": pr_readme,
    }
    page.route("https://api.github.com/**", api)
    page.route(
        f"{RAW}**",
        lambda route: route.fulfill(
            headers=CORS, body=files[route.request.url.removeprefix(RAW)]
        ),
    )
    page.route(
        "https://fonts.googleapis.com/**",
        lambda route: route.fulfill(content_type="text/css", body=""),
    )


def node(page, piece_id):
    return page.locator(f'button.node[aria-label^="{piece_id},"]')


def test_eng_108_map_shows_piece_in_open_pr_as_in_progress(page: Page, map_page):
    url, tree, ready = map_page
    claimed, built = ready[0], tree["already_working"][0]["id"]
    pr_readme = (
        f"### Working\n| `{built}` Example piece |\n"
        f"### In progress\n| `{claimed}` Example piece | `feat/example` |\n### Planned\n"
    )
    fake_github(page, MAIN_README, pr_readme)
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.set_viewport_size({"width": 360, "height": 800})

    page.goto(url)
    expect(page.locator("#live")).to_contain_text(
        "Live status from main at aaaaaaa and 1 open pull request"
    )
    expect(node(page, claimed)).to_have_class(re.compile(r"\bin_progress\b"))
    expect(node(page, claimed)).to_contain_text("#7")
    expect(node(page, built)).to_have_class(re.compile(r"\bworking\b"))

    node(page, claimed).click()
    expect(page.locator("aside a")).to_have_attribute(
        "href", f"https://github.com/{ftm.REPO}/pull/7"
    )
    assert errors == []


def test_eng_107_map_reads_working_from_main_live(page: Page, map_page):
    url, _, ready = map_page
    fake_github(
        page, f"### Working\n| `{ready[0]}` |\n### In progress\n### Planned\n", ""
    )

    page.goto(url)
    expect(page.locator("#live")).to_contain_text("Live status")
    expect(node(page, ready[0])).to_have_class(re.compile(r"\bworking\b"))


def test_eng_107_map_keeps_built_status_when_github_is_down(page: Page, map_page):
    url, _, ready = map_page
    fake_github(page, MAIN_README, "", api_status=403)

    page.goto(url)
    expect(page.locator("#live")).to_contain_text("Couldn't reach GitHub")
    expect(node(page, ready[0])).to_have_class(re.compile(r"\bready\b"))


def test_eng_110_map_zooms_in_out_and_fits(page: Page, map_page):
    url, _, _ = map_page
    fake_github(page, MAIN_README, "")
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.set_viewport_size({"width": 360, "height": 800})
    page.goto(url)
    level, tree_map = page.locator("#zoom-level"), page.locator("#map")
    expect(level).to_have_text("100%")
    start = tree_map.bounding_box()["width"]

    page.get_by_role("button", name="Zoom in").click()
    expect(level).to_have_text("125%")
    assert tree_map.bounding_box()["width"] > start

    page.get_by_role("button", name="Fit the whole tree").click()
    assert page.evaluate(
        "() => { const b = document.getElementById('mapbox');"
        " return b.scrollWidth <= b.clientWidth && b.scrollHeight <= b.clientHeight; }"
    )
    expect(page.get_by_role("button", name="Zoom out")).to_be_disabled()

    fitted = level.inner_text()
    box = page.locator("#mapbox").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.keyboard.down("Control")
    page.mouse.wheel(0, -300)
    page.keyboard.up("Control")
    expect(level).not_to_have_text(fitted)
    expect(page.get_by_role("button", name="Zoom out")).to_be_enabled()
    assert errors == []
