import pytest

from booktools.editsfile import Edit
from booktools.manuscript import BODY, Manuscript
from booktools.plan import plan
from booktools.report import edit_line

pytestmark = pytest.mark.tier1

LONG = (
    "At the start of a long paragraph, the chat window isn’t where the value is,"
    " and the paragraph then goes on for some while."
)


def line(text, find, replace, id="D7-14", why="D7: no contractions", status="PASS"):
    parts = {BODY: f"<w:document><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"}
    (found,) = plan([Edit(1, id, ("body",), find, replace, None, why)], Manuscript(parts), 0)
    return edit_line(found, text, "body, paragraph 1", status)


def test_shows_the_change_in_brackets_with_25_characters_either_side():
    assert line(LONG, "window isn’t where", "window is not where") == (
        "D7-14 | body, paragraph 1 | …ragraph, the chat window [isn’t → is not]"
        " where the value is, and … | D7: no contractions | PASS"
    )


def test_shows_no_ellipsis_where_the_paragraph_starts_or_ends():
    assert line("The cat sat.", "cat", "dog", status="found") == (
        "D7-14 | body, paragraph 1 | The [cat → dog] sat. | D7: no contractions | found"
    )


def test_an_insertion_and_a_deletion_show_an_empty_side():
    assert line("The cat sat.", "The cat", "The big cat", why="") == (
        "D7-14 | body, paragraph 1 | The [→ big ]cat sat. | | PASS"
    )
    assert line("The big cat sat.", "big cat", "cat", id="") == (
        "edit 1 | body, paragraph 1 | The [big  →]cat sat. | D7: no contractions | PASS"
    )
