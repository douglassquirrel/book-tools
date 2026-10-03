import pytest

from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES, Manuscript

pytestmark = pytest.mark.tier1


def p(text):
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def ref(kind, id):
    return f'<w:p><w:r><w:t>see</w:t></w:r><w:r><w:{kind}Reference w:id="{id}"/></w:r></w:p>'


def note(kind, id, *paragraphs, type=""):
    return f'<w:{kind} {type}w:id="{id}">' + "".join(paragraphs) + f"</w:{kind}>"


BOXED = "<w:p><w:r><w:drawing><w:txbxContent>" + p("in a box") + "</w:txbxContent></w:drawing></w:r></w:p>"
PARTS = {
    BODY: "<w:document><w:body>"
    + p("One")
    + BOXED
    + ref("endnote", 5)
    + ref("footnote", 2)
    + ref("endnote", 3)
    + "<w:sectPr/></w:body></w:document>",
    ENDNOTES: "<w:endnotes>"
    + note("endnote", -1, p("sep"), type='w:type="separator" ')
    + note("endnote", 3, p("Third in the file, second in the book"))
    + note("endnote", 5, p("First in the book"), p("its second paragraph"))
    + "</w:endnotes>",
    FOOTNOTES: "<w:footnotes>" + note("footnote", 2, p("A footnote")) + "</w:footnotes>",
}


def seen(parts, targets):
    return [(t.part, t.number, t.place, parts[t.part][t.start : t.end]) for t in targets]


def test_body_targets_are_numbered_over_every_paragraph_but_leave_out_text_boxes():
    m = Manuscript(PARTS)
    assert seen(PARTS, m.body) == [
        (BODY, 1, "body", p("One")),
        (BODY, 2, "body", BOXED),
        (BODY, 4, "body", ref("endnote", 5)),
        (BODY, 5, "body", ref("footnote", 2)),
        (BODY, 6, "body", ref("endnote", 3)),
    ]


def test_notes_are_counted_in_the_order_their_markers_appear_not_by_id():
    m = Manuscript(PARTS)
    assert [seen(PARTS, note) for note in m.endnotes] == [
        [
            (ENDNOTES, 3, "endnote:1", p("First in the book")),
            (ENDNOTES, 4, "endnote:1", p("its second paragraph")),
        ],
        [(ENDNOTES, 2, "endnote:2", p("Third in the file, second in the book"))],
    ]
    assert [seen(PARTS, note) for note in m.footnotes] == [
        [(FOOTNOTES, 1, "footnote:1", p("A footnote"))]
    ]


def test_a_document_with_no_notes_has_none():
    m = Manuscript({BODY: "<w:document><w:body>" + p("One") + "</w:body></w:document>"})
    assert (len(m.body), m.endnotes, m.footnotes) == (1, [], [])
