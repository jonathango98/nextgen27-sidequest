"""Load test of the Day 1 join moment, against staging only (ARCH-070 to ARCH-072, OPS-030).

Fake players join over a short spread, then keep My Code open while it refreshes, like
phones at the stage intro. It prints how fast each page answered and whether any failed,
then PASS or FAIL against the p95 target. Every number comes from `load_test` in
foundation/game-config.yaml (AI-013).

Connection scans and main screen polling are part of the ARCH-072 profile, but their pages
are not built yet. They join this test with their pieces (see NOT_TESTED_YET).

The host must be listed in LOAD_TEST_ALLOWED_HOSTS (comma-separated), which you set on your
own machine, so the test never runs against production by mistake.

Run from the repo root: python -m scripts.load_test --base-url https://<staging host>
"""

import argparse
import asyncio
import math
import os
import random
import re
import secrets
import sys
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx2

from app.auth import csrf
from app.config import load_config

ALLOWED_HOSTS_ENV = "LOAD_TEST_ALLOWED_HOSTS"

# Fake players are named "Load Test" / "Player <run>-<n>", so they are easy to spot and remove.
FIRST_NAME = "Load Test"

# A request slower than this counts as failed. A tool setting, not a game number.
TIMEOUT_SECONDS = 30

NOT_TESTED_YET = {
    "connection scans": "connections.meet",
    "main screen polling": "screen.main",
}

CHURCH_OPTION = re.compile(r'<option value="(\d+)"')
QR_REFRESH = re.compile(r"load delay:(\d+)s")


class LoadTestError(Exception):
    pass


@dataclass(frozen=True)
class Profile:
    signups: int
    spread_seconds: float
    play_seconds: float
    p95_target_ms: float


@dataclass(frozen=True)
class Result:
    phase: str
    route: str
    ms: float
    ok: bool
    why: str = ""  # for a failed request: the HTTP status or the error type
    recovered: bool = False  # a failed My Code refresh whose retry worked (DEC-031)


def profile_from_config(cfg: dict) -> Profile:
    lt = cfg["load_test"]  # ARCH-072, ARCH-070
    return Profile(
        signups=lt["signups"],
        spread_seconds=lt["signup_spread_seconds"],
        play_seconds=lt["play_minutes"] * 60,
        p95_target_ms=lt["p95_target_ms"],
    )


def check_host(base_url: str, allowed: str | None) -> None:
    """ARCH-071: staging only. Refuse any host not listed in LOAD_TEST_ALLOWED_HOSTS."""
    host = urlsplit(base_url).hostname
    hosts = {h.strip().lower() for h in (allowed or "").split(",") if h.strip()}
    if not host or host.lower() not in hosts:
        raise LoadTestError(
            f"Refused: {host or base_url!r} is not in {ALLOWED_HOSTS_ENV}. "
            "Add your staging host there. Never production."
        )


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile: pct% of the values are at or below the result."""
    ordered = sorted(values)
    return ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)]


def summarize(results: list[Result], target_ms: float) -> tuple[list[str], bool]:
    header = ("phase", "route", "requests", "failed", "p50 ms", "p95 ms", "max ms")
    lines = ["{:<6} {:<20} {:>8} {:>6} {:>7} {:>7} {:>7}".format(*header)]
    groups: dict[tuple[str, str], list[Result]] = {}
    for r in results:
        groups.setdefault((r.phase, r.route), []).append(r)
    for (phase, route), rs in groups.items():
        ms = [r.ms for r in rs]
        lines.append(
            f"{phase:<6} {route:<20} {len(rs):>8} {sum(not r.ok for r in rs):>6} "
            f"{percentile(ms, 50):>7.0f} {percentile(ms, 95):>7.0f} {max(ms):>7.0f}"
        )
    if not results:
        return [*lines, "FAIL: no requests were made"], False
    p95 = percentile([r.ms for r in results], 95)
    failed = sum(not r.ok and not r.recovered for r in results)
    recovered = sum(r.recovered for r in results)
    passed = p95 < target_ms and failed == 0
    lines.append(
        f"{'PASS' if passed else 'FAIL'}: p95 {p95:.0f} ms (target under "
        f"{target_ms:.0f} ms, ARCH-070), {failed} of {len(results)} requests failed, "
        f"{recovered} more worked on retry like the page does (DEC-031)"
    )
    reasons: dict[tuple[str, str, bool], int] = {}
    for r in results:
        if not r.ok:
            key = (r.route, r.why, r.recovered)
            reasons[key] = reasons.get(key, 0) + 1
    for (route, why, ok_on_retry), n in reasons.items():
        retry = ", worked on retry" if ok_on_retry else ""
        lines.append(f"Failed: {n} x {route}: {why}{retry}")
    for what, piece in NOT_TESTED_YET.items():
        lines.append(f"Not tested yet: {what}, comes with {piece}")
    return lines, passed


def _is_200(response: httpx2.Response) -> bool:
    return response.status_code == 200


class Phone:
    """One fake player's phone: its own cookies, and a note of every request's time."""

    def __init__(self, client: httpx2.AsyncClient, results: list[Result]):
        self.client = client
        self.results = results

    async def request(self, phase, route, method, url, expect, **kwargs):
        start = time.perf_counter()
        try:
            response = await self.client.request(method, url, **kwargs)
            ok = bool(expect(response))
            why = "" if ok else f"HTTP {response.status_code}"
        except httpx2.HTTPError as error:
            response, ok, why = None, False, type(error).__name__
        ms = (time.perf_counter() - start) * 1000
        self.results.append(Result(phase, route, ms, ok, why))
        self.last = len(self.results) - 1  # this phone's latest result
        return response if ok else None

    async def join(self, last_name: str, pin_digits: int) -> bool:
        """The three join steps a phone takes, then Home (API-002: HTMX headers)."""
        page = await self.request(
            "join",
            "GET /join",
            "GET",
            "/join",
            lambda r: r.status_code == 200 and CHURCH_OPTION.search(r.text),
        )
        if page is None:
            return False
        details = {
            csrf.FIELD: self.client.cookies.get(csrf.COOKIE, ""),
            "first_name": FIRST_NAME,
            "last_name": last_name,
            "church_id": random.choice(CHURCH_OPTION.findall(page.text)),
            "age_18_plus": "yes",  # fake adults only, no minors' data (SAFE-030)
        }
        htmx = {"HX-Request": "true"}
        if not await self.request(
            "join",
            "POST /join details",
            "POST",
            "/join",
            _is_200,
            data=details,
            headers=htmx,
        ):
            return False
        pin = "".join(secrets.choice("0123456789") for _ in range(pin_digits))
        if not await self.request(
            "join",
            "POST /join pin",
            "POST",
            "/join",
            lambda r: r.status_code == 204 and "HX-Redirect" in r.headers,
            data={**details, "step": "pin", "pin": pin, "pin_again": pin},
            headers=htmx,
        ):
            return False
        return bool(await self.request("join", "GET /", "GET", "/", _is_200))

    async def play(
        self, until: float, fallback_seconds: float, retry_seconds: float
    ) -> None:
        """Keep My Code open. It refreshes when the code changes, like the page does (ARCH-074)."""
        response = await self.request("play", "GET /code", "GET", "/code", _is_200)
        while (left := until - time.monotonic()) > 0:
            match = QR_REFRESH.search(response.text) if response else None
            wait = int(match.group(1)) if match else fallback_seconds
            await asyncio.sleep(min(wait, left))
            if time.monotonic() >= until:
                return
            response = await self.request(
                "play", "GET /code/qr", "GET", "/code/qr", _is_200
            )
            if response is None and until - time.monotonic() > retry_seconds:
                response = await self.retry_refresh(retry_seconds)

    async def retry_refresh(self, retry_seconds: float) -> httpx2.Response | None:
        """DEC-031: the page tries a failed refresh again, so a retry that works isn't a failure."""
        failed_at = self.last
        await asyncio.sleep(retry_seconds)
        response = await self.request(
            "play", "GET /code/qr retry", "GET", "/code/qr", _is_200
        )
        if response is not None:
            self.results[failed_at] = replace(self.results[failed_at], recovered=True)
        return response


async def run(
    base_url: str,
    profile: Profile,
    cfg: dict,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> list[Result]:
    results: list[Result] = []
    run_id = datetime.now(UTC).strftime("%m%d%H%M")
    start = time.monotonic()
    until = start + profile.spread_seconds + profile.play_seconds
    gap = profile.spread_seconds / profile.signups if profile.signups else 0

    async def one(n: int) -> None:
        await asyncio.sleep(start + n * gap - time.monotonic())
        async with httpx2.AsyncClient(
            base_url=base_url, transport=transport, timeout=TIMEOUT_SECONDS
        ) as client:
            phone = Phone(client, results)
            if await phone.join(f"Player {run_id}-{n + 1}", cfg["auth"]["pin_digits"]):
                qr = cfg["qr"]
                await phone.play(
                    until, qr["rotation_seconds"], qr["poll_retry_seconds"]
                )

    await asyncio.gather(*(one(n) for n in range(profile.signups)))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.load_test")
    parser.add_argument("--base-url", required=True, help="the staging address")
    args = parser.parse_args(argv)
    try:
        check_host(args.base_url, os.environ.get(ALLOWED_HOSTS_ENV))
    except LoadTestError as error:
        print(error, file=sys.stderr)
        return 2
    cfg = load_config()
    profile = profile_from_config(cfg)
    print(
        f"{profile.signups} fake players join over {profile.spread_seconds:.0f} s, "
        f"then keep My Code open for {profile.play_seconds / 60:.0f} min."
    )
    results = asyncio.run(run(args.base_url, profile, cfg))
    lines, passed = summarize(results, profile.p95_target_ms)
    print("\n".join(lines))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
