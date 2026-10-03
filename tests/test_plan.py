import pytest

from booktools.editsfile import Edit
from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES, Manuscript
from booktools.plan import PlanError, plan

pytestmark = pytest.mark.tier1


def p(*texts):
    return "<w:p>" + "".join(f"<w:r><w:t>{t}</w:t></w:r>" for t in texts) + "</w:p>"


def body(*paragraphs):
    return {BODY: "<w:document><w:body>" + "".join(paragraphs) + "</w:body></w:document>"}


def edit(index, find, replace, id="", where=("body",), occurrence=None):
    return Edit(index, id, where, find, replace, occurrence, "")


def summary(located):
    return [
        (
            l.edit.id, l.target.number, l.start, l.end,
            l.change.start, l.change.end, l.change.new, l.change.del_id, l.change.ins_id,
        )
        for l in located
    ]


def test_places_each_edit_and_numbers_revisions_in_document_order_whatever_the_file_order():
    m = Manuscript(body(p("The quick ", "brown fox"), p("jumps over the lazy dog")))
    edits = [
        edit(1, "lazy dog", "sleepy dog", "B"),
        edit(2, "quick brown", "slow brown", "A"),
        edit(3, " over", "", "C"),
    ]
    assert summary(plan(edits, m, highest_id=10)) == [
        ("A", 1, 4, 15, 4, 9, "slow", 11, 12),
        ("C", 2, 5, 10, 5, 10, "", 13, None),
        ("B", 2, 15, 23, 15, 19, "sleepy", 14, 15),
    ]


def problems(edits, manuscript):
    with pytest.raises(PlanError) as caught:
        plan(edits, manuscript, highest_id=0)
    return caught.value.problems


TWO = body(p("the cat and the hat"), p("on the mat"))


def test_text_that_is_not_there_is_an_error():
    assert problems([edit(1, "dog", "cat", "A1")], Manuscript(TWO)) == [
        'edit 1 (A1): "find" text not found in the body'
    ]


def test_text_found_more_than_once_needs_an_occurrence():
    assert problems([edit(1, "the", "a")], Manuscript(TWO)) == [
        'edit 1: "find" text occurs 3 times in the body (paragraphs 1, 1 and 2);'
        ' add "occurrence" to say which'
    ]


def test_occurrence_chooses_among_the_matches_counted_through_the_document():
    located = plan([edit(1, "the", "a", occurrence=3)], Manuscript(TWO), highest_id=0)
    assert [(l.target.number, l.start, l.end) for l in located] == [(2, 3, 6)]
    located = plan([edit(1, "the", "a", occurrence=2)], Manuscript(TWO), highest_id=0)
    assert [(l.target.number, l.start, l.end) for l in located] == [(1, 12, 15)]


def test_an_occurrence_beyond_the_last_match_is_an_error():
    assert problems([edit(1, "the", "a", occurrence=4)], Manuscript(TWO)) == [
        'edit 1: "occurrence" is 4 but the "find" text occurs 3 times in the body'
    ]
    assert problems([edit(1, "cat", "dog", occurrence=2)], Manuscript(TWO)) == [
        'edit 1: "occurrence" is 2 but the "find" text occurs once in the body'
    ]


def test_every_problem_is_reported_not_just_the_first():
    edits = [edit(1, "dog", "cat"), edit(2, "the cat", "a cat"), edit(3, "the", "a")]
    assert len(problems(edits, Manuscript(TWO))) == 2


def marker(kind, id):
    return f'<w:p><w:r><w:t>text</w:t></w:r><w:r><w:{kind}Reference w:id="{id}"/></w:r></w:p>'


NOTED = {
    BODY: "<w:document><w:body>"
    + p("the body says the word")
    + marker("endnote", 2)
    + marker("endnote", 1)
    + marker("footnote", 1)
    + "</w:body></w:document>",
    ENDNOTES: '<w:endnotes><w:endnote w:id="1">'
    + p("the second note")
    + '</w:endnote><w:endnote w:id="2">'
    + p("the first note")
    + "</w:endnote></w:endnotes>",
    FOOTNOTES: '<w:footnotes><w:footnote w:id="1">' + p("the footnote") + "</w:footnote></w:footnotes>",
}


def placed(edits, parts=NOTED):
    return [
        (l.target.place, l.target.part, l.target.number, l.start)
        for l in plan(edits, Manuscript(parts), highest_id=0)
    ]


def test_where_names_one_note_by_its_position_in_the_document():
    assert placed([edit(1, "the", "a", where=("endnote", 1))]) == [("endnote:1", ENDNOTES, 2, 0)]
    assert placed([edit(1, "the", "a", where=("endnote", 2))]) == [("endnote:2", ENDNOTES, 1, 0)]
    assert placed([edit(1, "the", "a", where=("footnote", 1))]) == [("footnote:1", FOOTNOTES, 1, 0)]


def test_where_all_searches_the_body_then_the_endnotes_then_the_footnotes():
    assert placed([edit(1, "note", "N", where=("all",), occurrence=n) for n in (3, 1, 2)]) == [
        ("endnote:1", ENDNOTES, 2, 10),
        ("endnote:2", ENDNOTES, 1, 11),
        ("footnote:1", FOOTNOTES, 1, 8),
    ]
    assert problems([edit(1, "nothing", "x", where=("all",))], Manuscript(NOTED)) == [
        'edit 1: "find" text not found in the body or the notes'
    ]


def test_the_body_alone_is_searched_by_default_and_a_note_alone_when_named():
    assert problems([edit(1, "second note", "x")], Manuscript(NOTED)) == [
        'edit 1: "find" text not found in the body'
    ]
    assert problems([edit(1, "body", "x", where=("endnote", 1))], Manuscript(NOTED)) == [
        'edit 1: "find" text not found in endnote:1'
    ]


def test_a_note_that_does_not_exist_is_an_error():
    assert problems([edit(1, "the", "a", where=("endnote", 3))], Manuscript(NOTED)) == [
        "edit 1: there is no endnote:3 (the document has 2 endnotes)"
    ]
    assert problems([edit(1, "the", "a", where=("footnote", 2))], Manuscript(NOTED)) == [
        "edit 1: there is no footnote:2 (the document has 1 footnote)"
    ]
    assert problems([edit(1, "the", "a", where=("footnote", 1))], Manuscript(TWO)) == [
        "edit 1: there is no footnote:1 (the document has no footnotes)"
    ]
