import pytest

from booktools.manuscript import Manuscript
from booktools.notes import read_notes
from tests.samples import BODY_PARAGRAPHS, W, note, sample_parts, separators

pytestmark = pytest.mark.tier1


def text_parts(parts):
    return {name: text for name, text in parts.items() if isinstance(text, str)}


def seen(parts):
    return [
        (n.place, n.text, n.sentence, n.heading, n.shown)
        for n in read_notes(Manuscript(text_parts(parts)))
    ]


def test_reads_each_note_with_its_text_its_sentence_and_where_the_book_puts_it():
    assert seen(sample_parts()) == [
        (
            "endnote:1",
            "Recorded by Trinity House in the station log.",
            "The lamp was lit at dusk, and the keeper isn’t one to waste oil.",
            "Chapter 1",
            1,
        ),
        ("endnote:2", "Ibid.", "The log for March is missing.", "Chapter 2", 2),
        (
            "footnote:1",
            "Imperial pints.",
            "She wrote every figure in a large ledger.",
            "Chapter 1",
            1,
        ),
    ]


def test_a_note_of_two_paragraphs_is_read_whole_and_a_marker_in_mid_sentence_takes_the_sentence():
    body = list(BODY_PARAGRAPHS)
    body[8] = (
        "<w:p><w:r><w:t>The log</w:t></w:r>"
        '<w:r><w:endnoteReference w:id="2"/></w:r>'
        "<w:r><w:t xml:space=\"preserve\"> for March is missing. It was never found.</w:t></w:r></w:p>"
    )
    parts = sample_parts(body)
    two = note("endnote", 2, "First paragraph.").replace(
        "</w:p></w:endnote>", "</w:p><w:p><w:r><w:t>Second paragraph.</w:t></w:r></w:p></w:endnote>"
    )
    parts["word/endnotes.xml"] = (
        f"<w:endnotes {W}>" + separators("endnote") + note("endnote", 1, "One.") + two + "</w:endnotes>"
    )
    assert seen(parts)[1] == (
        "endnote:2",
        "First paragraph.\nSecond paragraph.",
        "The log for March is missing.",
        "Chapter 2",
        2,
    )


def test_a_document_with_no_notes_has_none():
    parts = {"word/document.xml": f"<w:document {W}><w:body><w:p/></w:body></w:document>"}
    assert read_notes(Manuscript(parts)) == []
