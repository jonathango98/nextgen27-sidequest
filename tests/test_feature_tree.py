"""Feature tree checks (ENG-105 to ENG-110)."""

import re
from pathlib import Path

from scripts import feature_tree_map as ftm

FOUNDATION = Path(ftm.ROOT) / "foundation"


def _tree():
    tree, _, _ = ftm.load()
    return tree


def test_eng_105_piece_ids_are_unique_and_needs_exist():
    tree = _tree()
    ids = [p["id"] for p in tree["pieces"]]
    known = set(ids) | {p["id"] for p in tree["already_working"]}
    features = {f["id"] for f in tree["features"]}
    assert len(ids) == len(set(ids))
    for p in tree["pieces"]:
        assert p["feature"] in features, p["id"]
        assert p["id"].startswith(p["feature"] + "."), p["id"]
        assert set(p["needs"]) <= known, p["id"]


def test_eng_105_tree_has_no_cycles():
    tree = _tree()
    needs = {p["id"]: p["needs"] for p in tree["pieces"]}
    done = set()

    def visit(pid, path):
        assert pid not in path, f"cycle: {' -> '.join((*path, pid))}"
        if pid in done or pid not in needs:
            return
        for n in needs[pid]:
            visit(n, (*path, pid))
        done.add(pid)

    for pid in needs:
        visit(pid, ())


def test_eng_105_rule_ids_are_defined_in_the_foundation():
    text = "".join(f.read_text() for f in FOUNDATION.glob("*.md"))
    defined = set(re.findall(r"\*\*([A-Z]+-\d{3})\*\*", text))
    defined |= set(re.findall(r"^\| (DEC-\d{3}) \|", text, re.MULTILINE))
    for p in _tree()["pieces"]:
        assert set(p["rules"]) | set(p["open"]) <= defined, p["id"]


def test_eng_105_every_piece_says_what_and_how_to_try_it():
    for p in _tree()["pieces"]:
        assert p["what"].strip(), p["id"]
        assert p["try_it"].strip(), p["id"]


def test_eng_106_every_piece_is_size_s_or_m():
    for p in _tree()["pieces"]:
        assert p["size"] in {"S", "M"}, p["id"]


def test_eng_107_piece_is_ready_only_when_needs_are_working_and_not_locked():
    tree = {
        "already_working": [{"id": "a.done"}],
        "pieces": [
            {"id": "b.ready", "needs": ["a.done"], "open": []},
            {"id": "b.waiting", "needs": ["b.ready"], "open": []},
            {"id": "b.locked", "needs": ["a.done"], "open": ["GAME-999"]},
            {"id": "b.decided", "needs": ["a.done"], "open": ["GAME-998"]},
        ],
    }
    readme = "### Working\n\n### In progress\n\n### Planned\n"
    status = ftm.statuses(tree, readme, {"GAME-999": {}})
    assert status == {
        "a.done": "working",
        "b.ready": "ready",
        "b.waiting": "waiting",
        "b.locked": "decision",
        "b.decided": "ready",
    }


def test_eng_108_readme_rows_set_working_and_in_progress():
    tree = {
        "already_working": [],
        "pieces": [
            {"id": "c.one", "needs": [], "open": []},
            {"id": "c.two", "needs": ["c.one"], "open": []},
        ],
    }
    readme = (
        "### Working\n| `c.one` Example piece | 2026-10-26 |\n"
        "### In progress\n| `c.two` Example piece | `feat/c-two` |\n"
        "### Planned\n"
    )
    assert ftm.statuses(tree, readme, {}) == {
        "c.one": "working",
        "c.two": "in_progress",
    }


def test_eng_110_feature_tree_map_is_current():
    assert ftm.main(["--check"]) == 0, "Run: python scripts/feature_tree_map.py --write"
