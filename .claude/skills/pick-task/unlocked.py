"""List feature tree pieces by status, for the pick-task skill (ENG-105 to ENG-108).

Run from the repo root: python .claude/skills/pick-task/unlocked.py
Reads foundation/feature-tree.yaml, the README Project status, and the OPEN table in
foundation/13-decisions.md. Prints only; changes nothing.
"""

import re
import sys
from pathlib import Path

import yaml

TREE = "foundation/feature-tree.yaml"
README = "README.md"
DECISIONS = "foundation/13-decisions.md"


def section(text, start, end):
    i = text.index(start)
    return text[i : text.index(end, i)]


def main():
    tree = yaml.safe_load(Path(TREE).read_text())
    readme = Path(README).read_text()
    decisions = Path(DECISIONS).read_text()

    pieces = {p["id"]: p for p in tree["pieces"]}
    ids_in = lambda text: set(re.findall(r"`([a-z-]+\.[a-z-]+)`", text)) & set(pieces)
    working = {p["id"] for p in tree["already_working"]} | ids_in(
        section(readme, "### Working", "### In progress")
    )
    in_progress = ids_in(section(readme, "### In progress", "### Planned"))
    open_rules = set(
        re.findall(
            r"^\| ([A-Z]+-\d{3}) \|",
            section(decisions, "## 3. Open decisions", "## 4."),
            re.MULTILINE,
        )
    )
    unlocks = {i: sum(i in p["needs"] for p in pieces.values()) for i in pieces}

    ready, waiting, decision = [], [], []
    for pid, p in pieces.items():
        if pid in working or pid in in_progress:
            continue
        blocked_open = [r for r in p["open"] if r in open_rules]
        missing = [n for n in p["needs"] if n not in working]
        if blocked_open:
            decision.append(f"{pid}: needs a decision on {', '.join(blocked_open)}")
        elif missing:
            waiting.append(f"{pid}: waiting on {', '.join(missing)}")
        else:
            ready.append(p)

    print(f"READY ({len(ready)})")
    for p in ready:
        safety = ", safety review" if p["safety_review"] else ""
        print(
            f"- {p['id']} | {p['size']}, {p['level']}, {p['area']}{safety} | unlocks {unlocks[p['id']]}"
        )
        print(f"  what: {p['what']}")
        print(f"  learn: {p['learn']}")
        print(f"  rules: {', '.join(p['rules'])}")
    print(
        f"\nIN PROGRESS ({len(in_progress)}): {', '.join(sorted(in_progress)) or 'none'}"
    )
    print(f"\nWAITING ON OTHER PIECES ({len(waiting)})")
    print("\n".join(f"- {w}" for w in waiting))
    print(f"\nNEEDS A DECISION ({len(decision)})")
    print("\n".join(f"- {d}" for d in decision))


if __name__ == "__main__":
    sys.exit(main())
