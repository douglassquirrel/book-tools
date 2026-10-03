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


def heading(level, text, extra=""):
    return (
        f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr><w:r><w:t>{text}</w:t></w:r>{extra}</w:p>'
    )


def book(*paragraphs, **more):
    notes = "".join(note("endnote", n, p(f"note {n}")) for n in range(1, 6))
    feet = "".join(note("footnote", n, p(f"foot {n}")) for n in range(1, 3))
    parts = {
        BODY: "<w:document><w:body>" + "".join(paragraphs) + "<w:sectPr/></w:body></w:document>",
        ENDNOTES: "<w:endnotes>" + notes + "</w:endnotes>",
        FOOTNOTES: "<w:footnotes>" + feet + "</w:footnotes>",
    }
    parts.update(more)
    return Manuscript(parts)


SECTION_END = "<w:p><w:pPr><w:sectPr/></w:pPr></w:p>"
CHAPTERS = (
    ref("endnote", 1),
    heading(1, "Part One"),
    heading(2, "Chapter 1"),
    ref("endnote", 2),
    SECTION_END,
    heading(2, "Chapter 2", '<w:r><w:endnoteReference w:id="3"/></w:r>'),
    heading(3, "A subsection"),
    ref("endnote", 4),
    ref("footnote", 1),
)


def test_a_note_is_named_by_the_nearest_heading_and_its_number_when_notes_run_on():
    m = book(*CHAPTERS)
    assert [m.note_label("endnote", n) for n in (1, 2, 3, 4)] == [
        "note 1 (endnote:1)",
        "Chapter 1, note 2 (endnote:2)",
        "Chapter 2, note 3 (endnote:3)",
        "A subsection, note 4 (endnote:4)",
    ]
    assert m.note_label("footnote", 1) == "A subsection, note 1 (footnote:1)"


def test_a_note_is_numbered_within_its_section_when_notes_restart_there():
    settings = '<w:settings><w:endnotePr><w:numRestart w:val="eachSect"/></w:endnotePr></w:settings>'
    m = book(*CHAPTERS, **{"word/settings.xml": settings})
    assert [m.note_label("endnote", n) for n in (1, 2, 3, 4)] == [
        "note 1 (endnote:1)",
        "Chapter 1, note 2 (endnote:2)",
        "Chapter 2, note 1 (endnote:3)",
        # Under the heading at the level the section opens with, not the subsection.
        "Chapter 2, note 2 (endnote:4)",
    ]
    assert m.note_label("footnote", 1) == "A subsection, note 1 (footnote:1)"


def test_headings_are_known_by_the_style_s_name_when_the_styles_part_gives_one():
    styles = (
        '<w:styles><w:style w:type="paragraph" w:styleId="berschrift2"><w:name w:val="heading 2"/>'
        '</w:style><w:style w:type="paragraph" w:styleId="Heading9x"><w:name w:val="Body Text"/>'
        "</w:style></w:styles>"
    )
    german = '<w:p><w:pPr><w:pStyle w:val="berschrift2"/></w:pPr><w:r><w:t>Kapitel 1</w:t></w:r></w:p>'
    not_a_heading = '<w:p><w:pPr><w:pStyle w:val="Heading9x"/></w:pPr><w:r><w:t>Plain</w:t></w:r></w:p>'
    m = book(german, not_a_heading, ref("endnote", 1), **{"word/styles.xml": styles})
    assert m.note_label("endnote", 1) == "Kapitel 1, note 1 (endnote:1)"


def test_a_footnote_numbered_afresh_on_each_page_is_named_by_its_count_alone():
    body_setting = '<w:footnotePr><w:numRestart w:val="eachPage"/></w:footnotePr>'
    m = book(heading(1, "One"), ref("footnote", 1), "<w:p><w:pPr><w:sectPr>" + body_setting + "</w:sectPr></w:pPr></w:p>")
    assert m.note_label("footnote", 1) == "footnote:1"


def test_a_marker_with_no_note_behind_it_is_not_counted():
    parts = dict(PARTS)
    parts[BODY] = parts[BODY].replace("<w:sectPr/>", ref("endnote", 99) + "<w:sectPr/>")
    assert [note[0].place for note in Manuscript(parts).endnotes] == ["endnote:1", "endnote:2"]
