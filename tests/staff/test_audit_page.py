from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services import audit
from app.services.staff import create_account

FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)
FAKE_PIN_HASH = "not-a-real-hash"


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def _seed(test_db_path, browser_name):
    # The test server's database is shared, so each browser gets its own admin and players.
    conn = connect(test_db_path)
    try:
        admin = create_account(
            conn, f"test-admin-audit-{browser_name}", FAKE_PASSWORD, "admin"
        )
        conn.execute("INSERT OR IGNORE INTO church (name) VALUES ('Example Church A')")
        church = conn.execute(
            "SELECT id FROM church WHERE name = 'Example Church A'"
        ).fetchone()[0]
        a, b = (
            conn.execute(
                "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
                " VALUES (?, ?, 'Player', ?, 0, ?)",
                (
                    f"pub-audit-{n}-{browser_name}",
                    f"Audit{n}{browser_name}",
                    church,
                    FAKE_PIN_HASH,
                ),
            ).lastrowid
            for n in (1, 2)
        )
        conn.execute(
            "INSERT INTO connection (player_low_id, player_high_id, scanner_id, is_same_church)"
            " VALUES (?, ?, ?, 1)",
            (a, b, a),
        )
        audit.record(
            conn,
            actor_type="admin",
            actor_id=admin,
            action="points_revoke",
            target_type="player",
            target_id=a,
            reason="Example reason that is long enough to wrap onto a second line on a phone",
        )
    finally:
        conn.close()


def test_arch_050_admin_reads_the_log_and_activity_at_min_width(
    page: Page, live_server, test_db_path, browser_name, tmp_path
):
    _seed(test_db_path, browser_name)
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    page.goto(f"{live_server}/staff/login")
    page.get_by_label("Username").fill(f"test-admin-audit-{browser_name}")
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/admin")
    _fits(page)
    page.screenshot(path=tmp_path / "console.png", full_page=True)

    page.get_by_role("link", name="Log").click()
    page.wait_for_url(f"{live_server}/admin/audit")
    entry = page.locator("article", has_text="points revoke").first
    expect(entry).to_contain_text(f"Audit1{browser_name} P., Example Church A")
    expect(entry).to_contain_text(f"test-admin-audit-{browser_name} (admin)")
    _fits(page)
    page.screenshot(path=tmp_path / "log.png", full_page=True)

    # ARCH-062: the Activity tab lists players by connections.
    page.get_by_role("link", name="Activity").click()
    page.wait_for_url(f"{live_server}/admin/activity")
    expect(page.locator("article", has_text=f"Audit2{browser_name} P.")).to_be_visible()
    _fits(page)
    page.screenshot(path=tmp_path / "activity.png", full_page=True)
    assert errors == []
