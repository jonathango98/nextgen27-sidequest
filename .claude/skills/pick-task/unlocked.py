"""List feature tree pieces by status, for the pick-task skill (ENG-105 to ENG-108).

Run from the repo root: python .claude/skills/pick-task/unlocked.py
Add --tree to print only READY pieces, grouped by feature and numbered.
READY pieces are sorted by due date (PRD-054). A piece is due by its feature's due date, or
earlier if a piece that needs it is due sooner. Pieces past due are marked LATE.
Reads foundation/feature-tree.yaml, the README Project status, and the OPEN table in
foundation/13-decisions.md. Prints only; changes nothing.
"""

import re
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.feature_tree_map import due_dates

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
    due = due_dates(tree)
    today = date.today().isoformat()
    when = lambda i: f"due {due[i]}" + (" LATE" if due[i] < today else "")

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
    ready.sort(key=lambda p: (due[p["id"]], -unlocks[p["id"]]))

    if "--tree" in sys.argv:
        locked = {s.split(":")[0] for s in waiting + decision}
        print(f"READY ({len(ready)}), grouped by feature. Pick by number or piece ID.")
        n = 0
        for f in sorted(tree["features"], key=lambda f: str(f["due"])):
            mine = [p for p in ready if p["feature"] == f["id"]]
            if not mine:
                continue
            more = sum(pieces[i]["feature"] == f["id"] for i in locked)
            print(
                f"\n{f['name']} [{f['milestone']}, due {f['due']}]"
                + (f", {more} locked" if more else "")
            )
            for p in mine:
                n += 1
                safety = ", safety review" if p["safety_review"] else ""
                print(
                    f"  {n}. {p['id']} | {p['size']}, {p['level']}, {p['area']}{safety} | {when(p['id'])} | unlocks {unlocks[p['id']]}"
                )
                print(f"     {p['what']}")
                print(f"     try it: {p['try_it']}")
        return

    print(f"READY ({len(ready)})")
    for p in ready:
        safety = ", safety review" if p["safety_review"] else ""
        print(
            f"- {p['id']} | {p['size']}, {p['level']}, {p['area']}{safety} | {when(p['id'])} | unlocks {unlocks[p['id']]}"
        )
        print(f"  what: {p['what']}")
        print(f"  try it: {p['try_it']}")
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
