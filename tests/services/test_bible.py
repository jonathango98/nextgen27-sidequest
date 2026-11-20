import pytest

from app.services import bible


def test_wrap_012_bible_has_every_book_chapter_and_verse_in_niv_numbering():
    assert len(bible.VERSES) == 66
    assert sum(len(chapters) for chapters in bible.VERSES.values()) == 1189
    assert sum(sum(chapters) for chapters in bible.VERSES.values()) == 31103
    assert bible.VERSES["3 John"] == [15]  # the NIV has 15, the KJV 14
    assert list(bible.VERSES)[21] == "Song of Songs"  # NIV name, in Bible order


@pytest.mark.parametrize(
    ("book", "chapter", "verse", "saved"),
    [
        ("John", "3", "16", "John 3:16"),
        ("3 John", "1", "15", "3 John 1:15"),
        ("Psalms", "119", "176", "Psalms 119:176"),
        ("John", "22", "1", None),  # John has 21 chapters
        ("John", "3", "37", None),  # John 3 has 36 verses
        ("John", "0", "1", None),
        ("John", "²", "1", None),
        ("Johnn", "3", "16", None),
        ("", "", "", None),
    ],
)
def test_wrap_012_only_real_verses_make_an_answer(book, chapter, verse, saved):
    assert bible.reference(book, chapter, verse) == saved


@pytest.mark.parametrize(
    ("text", "ok"),
    [
        ("John 3:16", True),
        ("1 Corinthians 13:4", True),
        ("John 03:16", False),
        ("John 3:16 ", False),
        ("John", False),
        ("", False),
    ],
)
def test_wrap_012_saved_answer_must_be_in_the_exact_form(text, ok):
    assert bible.is_reference(text) is ok
