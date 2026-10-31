import re

import pytest
from fastapi.testclient import TestClient

from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.main import create_app
from app.routes.player import journal

FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=120)  # fake data (ENG-047)

# Each skeleton page and the tab it marks (UI-030, UI-037).
TABBED_PAGES = {
    "/": "Home",
    "/scan": "My Code",
    "/connections/1": "My Code",
    "/quests": "Quests",
    "/journal": "Home",
    "/journal/new": "Home",
    "/summary": "Home",
    "/box": "Home",
}
PAGES = (*TABBED_PAGES, "/wrapped")
TAB_HREFS = {"Home": "/", "My Code": "/code", "Quests": "/quests"}


def current_tab(href, label):
    # The current tab's link, with its icon before the label (07 section 3).
    return re.compile(
        rf'<a href="{re.escape(href)}" aria-current="page">(?:(?!</a>).)*?{re.escape(label)}\s*</a>',
        re.DOTALL,
    )


def main_buttons(html):
    # UI-035: a main button has the button class without button-secondary.
    classes = (c.split() for c in re.findall(r'class="([^"]*)"', html))
    return [c for c in classes if "button" in c and "button-secondary" not in c]


def link_to(href, label):
    # A link to href whose text includes label, allowing icons and pills around it.
    return re.compile(
        rf'<a [^>]*href="{re.escape(href)}"[^>]*>(?:(?!</a>).)*?\b{re.escape(label)}\b',
        re.DOTALL,
    )


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    return TestClient(app)


@pytest.mark.parametrize("path", PAGES)
def test_dec_061_skeleton_pages_logged_out_go_to_login(path):
    response = TestClient(create_app()).get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.parametrize("path", PAGES)
def test_dec_061_skeleton_pages_logged_out_htmx_go_to_login(path):
    response = TestClient(create_app()).get(path, headers={"HX-Request": "true"})
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/login"


@pytest.mark.parametrize("path", PAGES)
def test_ui_030_skeleton_pages_load(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize(("path", "tab"), TABBED_PAGES.items())
def test_ui_030_each_page_marks_its_tab(client, path, tab):
    html = client.get(path).text
    assert current_tab(TAB_HREFS[tab], tab).search(html)
    assert html.count('aria-current="page"') == 1


@pytest.mark.parametrize("path", PAGES)
def test_ui_035_each_page_has_at_most_one_main_button(client, path):
    assert len(main_buttons(client.get(path).text)) <= 1


@pytest.mark.parametrize("path", [p for p in TABBED_PAGES if p != "/"])
def test_ui_030_other_pages_show_score_in_top_bar(client, path):
    assert '<span class="score">120</span>' in client.get(path).text


def test_ui_030_home_top_bar_has_no_score(client):
    assert 'class="score"' not in client.get("/").text


def test_ui_036_home_shows_big_score(client):
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", client.get("/").text, re.DOTALL).group(1)
    assert re.sub(r"<[^>]+>", "", h1).split() == ["120", "points"]


@pytest.mark.parametrize(
    ("label", "href"),
    [
        ("Meet friends", "/scan"),
        ("Write", "/journal/new"),
        ("Read", "/summary"),
        ("Redeem box", "/box"),
    ],
)
def test_ui_036_home_links(client, label, href):
    assert link_to(href, label).search(client.get("/").text)


def test_ui_035_home_has_one_main_button(client):
    assert len(main_buttons(client.get("/").text)) == 1


def test_game_017_connection_id_must_be_a_number(client):
    assert client.get("/connections/abc").status_code != 200


def test_game_015_icebreaker_answer_is_switched_off(client):
    assert "<fieldset disabled>" in client.get("/connections/1").text


def test_game_031_journal_form_offers_three_choices(client):
    html = client.get("/journal/new").text
    for value in ("private", "shared_named", "shared_anonymous"):
        assert f'name="visibility" value="{value}"' in html


def test_ui_031_journal_form_explains_anonymous(client):
    note = (
        "Anonymous hides your name from other players. "
        "Game organizers can still see who wrote it."
    )
    assert note in client.get("/journal/new").text


def test_game_036_journal_form_is_switched_off(client):
    assert "<fieldset disabled>" in client.get("/journal/new").text


def test_ui_030_journal_links_to_new_takeaway(client):
    assert 'href="/journal/new">Write a takeaway</a>' in client.get("/journal").text


def test_game_073_open_box_says_where_to_claim(client):
    html = client.get("/box").text
    assert "Go to the game booth when it's open." in html
    assert 'href="/code">My Code</a>' in html


def test_wrap_002_wrapped_shows_unlock_message(client):
    html = client.get("/wrapped").text
    assert "Your Wrapped unlocks on Sunday." in html
    assert 'href="/">Close</a>' in html
    assert 'aria-label="Main"' not in html


def test_ui_036_home_numbers_come_from_config(client):
    cfg = load_config()
    html = client.get("/").text
    # AI-013: the Write pill and the box size come from game-config.yaml.
    assert f'<span class="pill">+{cfg["points"]["journal_takeaway"]}</span>' in html
    milestone = cfg["blind_box"]["milestone_points"]
    assert f'aria-valuemax="{milestone}"' in html
    assert f"/ {milestone}</span>" in html


def test_ui_038_summary_groups_by_session_in_order(client):
    html = client.get("/summary").text
    titles = re.findall(r'<h2 class="session-title"[^>]*>([^<]+)</h2>', html)
    assert titles == [s["session"] for s in journal.PLACEHOLDER_SUMMARY]


def test_safe_004_summary_shows_first_name_and_church_or_anonymous(client):
    html = client.get("/summary").text
    authors = re.findall(r'<p class="takeaway-author">([^<]+)</p>', html)
    expected = [
        "Anonymous" if t.get("anonymous") else f"{t['first_name']} · {t['church']}"
        for s in journal.PLACEHOLDER_SUMMARY
        for t in s["takeaways"]
    ]
    assert authors == expected
    assert "Anonymous" in authors


def test_game_030_journal_word_count_uses_config_minimum(client):
    minimum = load_config()["limits"]["journal_min_words"]
    assert f"0 / {minimum} words" in client.get("/journal/new").text


def test_game_036_journal_shows_a_session_name(client):
    html = client.get("/journal/new").text
    assert (
        f'<p class="page-sub">{journal.PLACEHOLDER_SUMMARY[-1]["session"]}</p>' in html
    )
