"""Draw the feature tree with live status (ENG-105 to ENG-108).

Reads foundation/feature-tree.yaml, the README Project status, and the OPEN table in
foundation/13-decisions.md, then writes:

- docs/feature-tree.md, a Mermaid diagram GitHub draws in place (--write, or --check
  to fail when it is out of date)
- an interactive HTML page for GitHub Pages (--html PATH)

Run from the repo root: python scripts/feature_tree_map.py --write
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TREE = ROOT / "foundation" / "feature-tree.yaml"
README = ROOT / "README.md"
DECISIONS = ROOT / "foundation" / "13-decisions.md"
MAP_MD = ROOT / "docs" / "feature-tree.md"
TEMPLATE = Path(__file__).with_name("feature_tree_map.html")
PAGES_URL = "https://jonathango98.github.io/nextgen27-sidequest/"
REPO = "jonathango98/nextgen27-sidequest"

LABELS = {
    "working": "Working",
    "in_progress": "In progress",
    "ready": "Ready",
    "waiting": "Waiting",
    "decision": "Needs decision",
}


def _section(text, start, end):
    i = text.index(start)
    return text[i : text.index(end, i)]


def load():
    tree = yaml.safe_load(TREE.read_text())
    readme = README.read_text()
    decisions = DECISIONS.read_text()
    open_table = _section(decisions, "## 3. Open decisions", "## 4.")
    open_rules = {
        rule: {"q": question.strip(), "owner": owner.strip()}
        for rule, question, owner in re.findall(
            r"^\| ([A-Z]+-\d{3}) \| ([^|]+) \|[^|]*\| ([^|]+) \|",
            open_table,
            re.MULTILINE,
        )
    }
    return tree, readme, open_rules


def statuses(tree, readme, open_rules):
    """Status of every piece, by ENG-107 and ENG-108."""
    ids = {p["id"] for p in tree["pieces"]} | {p["id"] for p in tree["already_working"]}

    def ids_in(text):
        return set(re.findall(r"`([a-z-]+\.[a-z-]+)`", text)) & ids

    working = {p["id"] for p in tree["already_working"]}
    working |= ids_in(_section(readme, "### Working", "### In progress"))
    in_progress = ids_in(_section(readme, "### In progress", "### Planned"))

    result = {i: "working" for i in working}
    for p in tree["pieces"]:
        pid = p["id"]
        if pid in working:
            continue
        if pid in in_progress:
            result[pid] = "in_progress"
        elif any(r in open_rules for r in p["open"]):
            result[pid] = "decision"
        elif all(n in working for n in p["needs"]):
            result[pid] = "ready"
        else:
            result[pid] = "waiting"
    return result


def due_dates(tree):
    """Due date of every piece (PRD-054): its feature's due date, or earlier if a piece
    that needs it is due sooner."""
    feature_due = {f["id"]: str(f["due"]) for f in tree["features"]}
    pieces = {p["id"]: p for p in tree["pieces"]}
    due = {}

    def visit(pid):
        if pid not in due:
            due[pid] = min(
                [feature_due[pieces[pid]["feature"]]]
                + [visit(q) for q, p in pieces.items() if pid in p["needs"]]
            )
        return due[pid]

    for pid in pieces:
        visit(pid)
    return due


def due_label(day):
    d = date.fromisoformat(day)
    return f"Due {d:%a %b} {d.day}"


def render_markdown(tree, status, open_rules):
    def node_id(pid):
        return pid.replace(".", "_").replace("-", "_")

    due = due_dates(tree)
    lines = ["```mermaid", "flowchart LR"]
    lines.append("  subgraph built [Already working]")
    lines += [f'    {node_id(p["id"])}["{p["id"]}"]' for p in tree["already_working"]]
    lines.append("  end")
    for day in sorted(set(due.values())):
        lines.append(f'  subgraph w_{day.replace("-", "_")} ["{due_label(day)}"]')
        for p in tree["pieces"]:
            if due[p["id"]] == day:
                lines.append(
                    f'    {node_id(p["id"])}["{p["id"]}<br/>{p["size"]} · {p["level"]}"]'
                )
        lines.append("  end")
    for p in tree["pieces"]:
        lines += [f"  {node_id(n)} --> {node_id(p['id'])}" for n in p["needs"]]
    lines += [
        "  classDef working fill:#e6f2e9,stroke:#1e7b3a,color:#14151a",
        "  classDef in_progress fill:#e8eefc,stroke:#1f4fd1,color:#14151a",
        "  classDef ready fill:#fff4d6,stroke:#a87400,stroke-width:3px,color:#14151a",
        "  classDef waiting fill:#f1f0eb,stroke:#c3c0b6,color:#545a66",
        "  classDef decision fill:#fdeeec,stroke:#b42318,stroke-dasharray:4 3,color:#14151a",
    ]
    for s in LABELS:
        members = sorted(node_id(i) for i, v in status.items() if v == s)
        if members:
            lines.append(f"  class {','.join(members)} {s}")
    lines.append("```")

    pieces = {p["id"]: p for p in tree["pieces"]}
    counts = {s: sum(v == s for v in status.values()) for s in LABELS}

    def listing(state, extra):
        ids = sorted((i for i in pieces if status[i] == state), key=lambda i: due[i])
        rows = [f"- `{i}`: {extra(pieces[i])}" for i in ids]
        return rows or ["- None"]

    out = [
        "# Feature tree map",
        "",
        "> Generated by `python scripts/feature_tree_map.py --write`. Do not edit by hand.",
        f"> Interactive version: {PAGES_URL}",
        "",
        (
            "Every planned piece of work and what it needs first (ENG-105 to ENG-108), "
            "grouped by the week it is due (PRD-054). Pieces flow left to right in time: "
            "finishing one unlocks the pieces it points to. Run `/pick-task` to claim one."
        ),
        "",
        " · ".join(f"**{LABELS[s]}** {counts[s]}" for s in LABELS),
        "",
        (
            "Colors: green Working, blue In progress, gold Ready, gray Waiting, "
            "red dashed Needs decision."
        ),
        "",
        *lines,
        "",
        "## Ready now",
        "",
        *listing(
            "ready",
            lambda p: (
                f"{p['what']} ({p['size']}, {p['level']}, {p['area']}, "
                f"{due_label(due[p['id']]).lower()})"
                f"\n  - Try it: {p['try_it']}"
            ),
        ),
        "",
        "## In progress",
        "",
        *listing("in_progress", lambda p: p["what"]),
        "",
        "## Needs a decision",
        "",
        *listing(
            "decision",
            lambda p: "; ".join(
                f"{r} ({open_rules[r]['owner']})" for r in p["open"] if r in open_rules
            ),
        ),
        "",
    ]
    return "\n".join(out)


def render_html(tree, status, open_rules, source):
    data = {
        "built": tree["already_working"],
        "features": tree["features"],
        "pieces": tree["pieces"],
        "status": status,
        "due": due_dates(tree),
        "open": {
            r: v
            for r, v in open_rules.items()
            if any(r in p["open"] for p in tree["pieces"])
        },
        "source": source,
        "repo": REPO,
    }
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.read_text().replace("__DATA__", payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write", action="store_true", help="update docs/feature-tree.md"
    )
    parser.add_argument(
        "--check", action="store_true", help="fail if docs/feature-tree.md is stale"
    )
    parser.add_argument(
        "--html", type=Path, help="write the interactive page to this path"
    )
    parser.add_argument(
        "--source", default="local", help="commit or label shown on the page"
    )
    args = parser.parse_args(argv)

    tree, readme, open_rules = load()
    status = statuses(tree, readme, open_rules)
    markdown = render_markdown(tree, status, open_rules)

    if args.check and (not MAP_MD.exists() or MAP_MD.read_text() != markdown):
        print(
            "docs/feature-tree.md is out of date. Run: python scripts/feature_tree_map.py --write"
        )
        return 1
    if args.write:
        MAP_MD.parent.mkdir(exist_ok=True)
        MAP_MD.write_text(markdown)
    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_html(tree, status, open_rules, args.source))
    return 0


if __name__ == "__main__":
    sys.exit(main())
