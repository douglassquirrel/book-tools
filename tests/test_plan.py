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
