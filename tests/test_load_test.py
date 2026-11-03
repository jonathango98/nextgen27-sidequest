import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.auth import session
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.services import qr
from scripts import load_test as lt

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
CHURCHES = ("Example Church A", "Example Church B")
STAGING = "https://staging.example.test"


def _results(ms_list, ok=True):
    return [lt.Result("join", "GET /join", ms, ok) for ms in ms_list]


def test_arch_071_refuses_host_not_allowed():
    with pytest.raises(lt.LoadTestError):
        lt.check_host(STAGING, None)
    with pytest.raises(lt.LoadTestError):
        lt.check_host("https://prod.example.test", "staging.example.test")


def test_arch_071_allows_listed_host():
    lt.check_host(STAGING, "other.example.test, Staging.Example.Test")


def test_arch_071_main_refuses_before_any_request(monkeypatch):
    monkeypatch.delenv(lt.ALLOWED_HOSTS_ENV, raising=False)
    assert lt.main(["--base-url", STAGING]) == 2


def test_arch_072_profile_reads_config():
    cfg = load_config()
    profile = lt.profile_from_config(cfg)
    assert profile.signups == cfg["load_test"]["signups"]
    assert profile.spread_seconds == cfg["load_test"]["signup_spread_seconds"]
    assert profile.play_seconds == cfg["load_test"]["play_minutes"] * 60
    assert profile.p95_target_ms == cfg["load_test"]["p95_target_ms"]


def test_arch_070_p95_is_nearest_rank():
    values = list(range(1, 101))
    assert lt.percentile(values, 95) == 95
    assert lt.percentile(values, 50) == 50
    assert lt.percentile([7], 95) == 7


def test_arch_070_summary_passes_under_target():
    target = load_config()["load_test"]["p95_target_ms"]
    lines, passed = lt.summarize(_results([target / 2] * 20), target)
    assert passed
    assert lines[-len(lt.NOT_TESTED_YET) - 1].startswith("PASS")


def test_arch_070_summary_fails_over_target():
    target = load_config()["load_test"]["p95_target_ms"]
    _, passed = lt.summarize(_results([target / 2] * 18 + [target * 2] * 2), target)
    assert not passed


def test_arch_070_summary_fails_on_any_failed_request():
    target = load_config()["load_test"]["p95_target_ms"]
    results = _results([target / 2] * 19) + _results([target / 2], ok=False)
    _, passed = lt.summarize(results, target)
    assert not passed


def test_arch_070_summary_says_why_requests_failed():
    target = load_config()["load_test"]["p95_target_ms"]
    failed = [lt.Result("join", "GET /join", target / 2, False, "HTTP 502")] * 2
    lines, _ = lt.summarize(_results([target / 2] * 18) + failed, target)
    assert "Failed: 2 x GET /join: HTTP 502" in lines


def test_dec_031_summary_passes_when_retry_worked():
    target = load_config()["load_test"]["p95_target_ms"]
    failed = lt.Result("play", "GET /code/qr", target / 2, False, "ConnectError", True)
    lines, passed = lt.summarize(_results([target / 2] * 19) + [failed], target)
    assert passed
    assert "Failed: 1 x GET /code/qr: ConnectError, worked on retry" in lines


def test_dec_031_failed_refresh_is_retried_once():
    calls = []

    def answer(request):
        calls.append(request.url.path)
        if request.url.path == "/code/qr" and calls.count("/code/qr") == 1:
            raise httpx2.ConnectError("fake dropped connection")
        return httpx2.Response(200, text="no refresh delay here")

    async def go():
        results = []
        transport = httpx2.MockTransport(answer)
        async with httpx2.AsyncClient(base_url=STAGING, transport=transport) as c:
            # Tiny waits so the test is quick. Not the real refresh times.
            await lt.Phone(c, results).play(time.monotonic() + 0.3, 0.05, 0.01)
        return results

    with ThreadPoolExecutor(1) as pool:  # the browser tests leave a loop running
        results = pool.submit(asyncio.run, go()).result()
    first, retry = results[1], results[2]
    assert (first.route, first.ok, first.recovered) == ("GET /code/qr", False, True)
    assert (retry.route, retry.ok) == ("GET /code/qr retry", True)


def test_arch_070_summary_fails_with_no_requests():
    _, passed = lt.summarize([], load_config()["load_test"]["p95_target_ms"])
    assert not passed


@pytest.fixture
def app(monkeypatch, tmp_path):
    db_path = tmp_path / "load.db"
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    app = create_app()
    with TestClient(app):  # runs the migrations
        conn = connect(db_path)
        conn.executemany(
            "INSERT INTO church (name) VALUES (?)", [(n,) for n in CHURCHES]
        )
        conn.close()
        yield app, db_path


def test_arch_072_fake_players_join_then_open_my_code(app):
    app, db_path = app
    cfg = load_config()
    # A tiny run, not the real profile: a few phones, no spread, a moment of play.
    profile = lt.Profile(signups=3, spread_seconds=0, play_seconds=0.1, p95_target_ms=1)
    transport = httpx2.ASGITransport(app=app)
    # Its own thread: the browser tests leave an event loop running in this one.
    with ThreadPoolExecutor(1) as pool:
        run = lt.run("https://testserver", profile, cfg, transport)
        results = pool.submit(asyncio.run, run).result()

    assert all(r.ok for r in results), [r for r in results if not r.ok]
    routes = [r.route for r in results]
    for route in (
        "GET /join",
        "POST /join details",
        "POST /join pin",
        "GET /",
        "GET /code",
    ):
        assert routes.count(route) == profile.signups

    conn = connect(db_path)
    players = conn.execute("SELECT first_name, is_under_18 FROM player").fetchall()
    conn.close()
    assert len(players) == profile.signups
    assert all(
        p["first_name"] == lt.FIRST_NAME and not p["is_under_18"] for p in players
    )
