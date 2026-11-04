from playwright.sync_api import Page, expect

from app.config import load_config
from app.routes.player.quests import quest_list


def test_game_040_quests_list_fits_at_360(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.goto(f"{live_server}/quests")
    rows = page.locator(".quest")
    expect(rows).to_have_count(len(quest_list(load_config())))
    tap_min = load_config()["ui"]["min_tap_target_px"]
    for i in range(rows.count()):
        assert rows.nth(i).bounding_box()["height"] >= tap_min
    width = load_config()["ui"]["min_viewport_px"]
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    assert problems == []
