from playwright.sync_api import Page, expect

from app.config import load_config


def test_game_073_open_box_layout_at_360(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.goto(f"{live_server}/box")
    tiles = page.locator(".box-tile")
    expect(tiles).to_have_count(load_config()["blind_box"]["max_per_player"])
    tops = {round(tiles.nth(i).bounding_box()["y"]) for i in range(tiles.count())}
    assert len(tops) == 1  # the boxes sit in one row
    card = page.locator(".how-to-claim").bounding_box()
    my_code = page.get_by_role("link", name="My Code", exact=True).last.bounding_box()
    assert my_code["y"] >= card["y"] + card["height"]
    width = load_config()["ui"]["min_viewport_px"]
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    assert problems == []
