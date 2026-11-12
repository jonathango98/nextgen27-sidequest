from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services.staff import create_account

FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)
FAKE_PIN_HASH = "not-a-real-hash"


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def _seed(test_db_path, browser_name):
    # The test server's database is shared, so each browser gets its own admin, writer, and notes.
    conn = connect(test_db_path)
    try:
        create_account(
            conn, f"test-admin-review-{browser_name}", FAKE_PASSWORD, "admin"
        )
        conn.execute("INSERT OR IGNORE INTO church (name) VALUES ('Example Church A')")
        church = conn.execute(
            "SELECT id FROM church WHERE name = 'Example Church A'"
        ).fetchone()[0]
        player = conn.execute(
            "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
            " VALUES (?, 'Test', ?, ?, 0, ?)",
            (
                f"pub-review-{browser_name}",
                f"Reviewed {browser_name}",
                church,
                FAKE_PIN_HASH,
            ),
        ).lastrowid
        session = conn.execute(
            "INSERT INTO session (public_id, title, ended_at) VALUES (?, ?, ?)",
            (
                f"pub-review-s-{browser_name}",
                f"Example Session review {browser_name}",
                "2027-03-05T10:00:00Z",
            ),
        ).lastrowid
        texts = {}
        for kind in ("approve", "reject"):
            texts[kind] = f"Example takeaway to {kind} in {browser_name}."
            conn.execute(
                "INSERT INTO takeaway (player_id, session_id, text, visibility, review_status)"
                " VALUES (?, ?, ?, 'shared_anonymous', 'pending')",
                (player, session, texts[kind]),
            )
        return texts
    finally:
        conn.close()


def test_safe_040_admin_approves_and_rejects_at_min_width(
    page: Page, live_server, test_db_path, browser_name, tmp_path
):
    texts = _seed(test_db_path, browser_name)
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("dialog", lambda d: d.accept())  # Reject asks first (hx-confirm)

    page.goto(f"{live_server}/staff/login")
    page.get_by_label("Username").fill(f"test-admin-review-{browser_name}")
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/admin")
    page.get_by_role("link", name="Review notes").click()
    page.wait_for_url(f"{live_server}/admin/review")
    _fits(page)
    page.screenshot(path=tmp_path / "review-waiting.png", full_page=True)

    # SAFE-009: the admin sees who wrote an anonymous note.
    approve = page.locator("article", has_text=texts["approve"])
    expect(approve).to_contain_text(f"Test Reviewed {browser_name}, Example Church A")
    approve.get_by_role("button", name="Approve").click()
    expect(page.get_by_role("status")).to_contain_text("Approved.")
    expect(page.locator("article", has_text=texts["approve"])).to_have_count(0)

    page.locator("article", has_text=texts["reject"]).get_by_role(
        "button", name="Reject"
    ).click()
    expect(page.get_by_role("status")).to_contain_text("Rejected.")
    expect(page.locator("article", has_text=texts["reject"])).to_have_count(0)
    _fits(page)

    # DEC-076: a rejected note can be approved later from the Rejected tab.
    page.get_by_role("link", name="Rejected").click()
    rejected = page.locator("article", has_text=texts["reject"])
    expect(rejected.get_by_role("button", name="Approve")).to_be_visible()
    _fits(page)
    page.screenshot(path=tmp_path / "review-rejected.png", full_page=True)
    assert errors == []
