"""Bible books and verse counts for the favorite verse pickers (WRAP-012, GAME-019).

Not game numbers, so they live here and not in game-config.yaml (AI-013). Each book maps
to the number of verses in each chapter, in NIV numbering: the public-domain KJV counts,
with 3 John at 15 verses as in the NIV (66 books, 1,189 chapters, 31,103 verses).

The words shown for a pick are the ASV (1901, public domain, DEC-083), from
github.com/scrollmapper/bible_databases (59b18c5, formats/json/ASV.json), without its
stray "[" before Selah and Higgaion and the Psalm 119 headings stuck to the verse before.
"""

import json
from pathlib import Path

VERSES: dict[str, list[int]] = json.loads(
    (Path(__file__).with_name("bible_verses.json")).read_text()
)
ASV: dict[str, list[list[str]]] = json.loads(
    (Path(__file__).with_name("bible_asv.json")).read_text(encoding="utf-8")
)
MAX_CHAPTERS = max(len(chapters) for chapters in VERSES.values())
MAX_VERSES = max(max(chapters) for chapters in VERSES.values())


def reference(book: str, chapter: str, verse: str) -> str | None:
    """The answer as saved, like "John 3:16", or None if that verse doesn't exist.

    shortcut: allows every number up to a chapter's last verse, including the few the NIV
    leaves out of the text (like Acts 8:37), which is fine for matching (WRAP-012).
    """
    chapters = VERSES.get(book)
    if not chapters or not (chapter.isdecimal() and verse.isdecimal()):
        return None
    if max(len(chapter), len(verse)) > 3:  # int() raises on thousands of digits
        return None
    c, v = int(chapter), int(verse)
    if not (1 <= c <= len(chapters) and 1 <= v <= chapters[c - 1]):
        return None
    return f"{book} {c}:{v}"


def asv_text(book: str, chapter: str, verse: str) -> str:
    """That verse's words, or "" if it doesn't exist or the ASV has no words for it."""
    if reference(book, chapter, verse) is None:
        return ""
    verses = ASV[book][int(chapter) - 1]
    # 3 John 1:15 is in NIV numbering only.
    return verses[int(verse) - 1] if int(verse) <= len(verses) else ""


def is_reference(text: str) -> bool:
    """True if text is a saved verse answer in exactly the WRAP-012 form."""
    book, _, numbers = text.rpartition(" ")
    chapter, _, verse = numbers.partition(":")
    return reference(book, chapter, verse) == text
