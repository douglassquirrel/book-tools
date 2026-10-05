import pytest

from booktools.editsfile import Edit
from booktools.manuscript import BODY, Manuscript
from booktools.plan import plan
from booktools.report import edge_notes, edit_line

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


def notes(text, find, replace, id="C"):
    parts = {BODY: f"<w:document><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"}
    (found,) = plan([Edit(1, id, ("body",), find, replace, None, "")], Manuscript(parts), 0)
    return edge_notes(found, text)


def test_a_sentence_cut_from_between_two_others_leaves_two_spaces_and_the_report_says_so():
    text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. Pellentesque sed."
    assert notes(text, "Sed non risus.", "") == [
        'note: accepting C leaves two spaces in a row: "…ing elit.  Pellentes…"'
    ]
    assert notes(text, "Sed non risus. ", "") == []  # cut with its space: nothing to say
    assert notes(text, "Sed non risus.", "", id="") == [
        'note: accepting edit 1 leaves two spaces in a row: "…ing elit.  Pellentes…"'
    ]


def test_words_run_together_or_a_space_left_before_punctuation_are_noted():
    assert notes("The cat sat on the mat.", "cat ", "dog") == [
        'note: accepting C runs two words together: "The dogsat on the…"'
    ]
    assert notes("The cat, the dog and the bird.", "cat", "") == [
        'note: accepting C leaves a space before a punctuation mark: "The , the dog …"'
    ]
    assert notes("Red, green and blue.", "Red", "Red,") == [
        'note: accepting C leaves a punctuation mark doubled: "Red,, green an…"'
    ]
    assert notes("It ended. Then it began.", "ended. ", "ended.") == [
        'note: accepting C leaves no space after a punctuation mark: "It ended.Then it be…"'
    ]


def test_an_ordinary_change_and_one_at_either_end_of_the_paragraph_give_no_note():
    assert notes("The cat sat on the mat.", "cat", "dog") == []
    assert notes("The cat sat on the mat.", "The cat", "A cat") == []
    assert notes("The cat sat on the mat.", "the mat.", "a mat.") == []
    assert notes("The cat sat on the mat.", "sat ", "") == []
    assert notes("The cat sat.", "The cat sat.", "") == []


def test_what_was_already_so_before_the_edit_is_not_blamed_on_it():
    # Two spaces, a web address and a decimal that the edit only stands beside.
    assert notes("One.  Two three.", "Two", "2") == []
    assert notes("See example.com for more.", "com", "org") == []
    assert notes("It was 3.5 pints.", "5", "75") == []
