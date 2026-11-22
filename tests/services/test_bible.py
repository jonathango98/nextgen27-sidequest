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
        ("John", "9" * 4301, "1", None),  # too many digits for int()
        ("John", "1", "9" * 4301, None),
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


def test_dec_083_asv_lines_up_with_the_pickers():
    assert list(bible.ASV) == list(bible.VERSES)
    for book, chapters in bible.VERSES.items():
        want = [14] if book == "3 John" else chapters
        assert [len(verses) for verses in bible.ASV[book]] == want, book


@pytest.mark.parametrize(
    ("book", "chapter", "verse", "start", "end"),
    [
        ("John", "3", "16", "For God so loved the world", "eternal life."),
        ("Song of Songs", "1", "1", "The Song of songs", "Solomon\u2019s."),
        ("Psalms", "3", "2", "Many there are", "in God. Selah"),
        ("Psalms", "119", "8", "I will observe", "forsake me not utterly."),
        ("John", "7", "53", "[And they went", "his own house:"),
        ("John", "8", "11", "And she said", "sin no more.]"),
    ],
)
def test_dec_083_asv_text_of_a_pick(book, chapter, verse, start, end):
    text = bible.asv_text(book, chapter, verse)
    assert text.startswith(start) and text.endswith(end), text


def test_dec_083_asv_has_no_stray_marks():
    marked = [
        f"{book} {c}:{v}"
        for book, chapters in bible.ASV.items()
        for c, verses in enumerate(chapters, 1)
        for v, text in enumerate(verses, 1)
        if any(mark in "[]" or "\u0590" <= mark <= "\u05ff" for mark in text)
    ]
    assert marked == ["John 7:53", "John 8:11"]  # the ASV's own brackets


@pytest.mark.parametrize(
    ("book", "chapter", "verse"),
    [
        ("3 John", "1", "15"),  # NIV numbering only
        ("Acts", "8", "37"),  # left out of the ASV
        ("John", "22", "1"),
        ("", "1", "1"),
    ],
)
def test_dec_083_no_words_gives_no_text(book, chapter, verse):
    assert bible.asv_text(book, chapter, verse) == ""
