import pytest

from booktools.paragraph import Paragraph

pytestmark = pytest.mark.tier1


def test_joins_the_text_of_runs_and_decodes_entities():
    xml = (
        "<w:p><w:pPr><w:rPr><w:b/></w:rPr></w:pPr>"
        "<w:r><w:t>Tom &amp; </w:t></w:r>"
        '<w:proofErr w:type="spellStart"/>'
        '<w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">Jerry&#8217;s &lt;b&gt;</w:t></w:r>'
        "</w:p>"
    )
    assert Paragraph(xml).text == "Tom & Jerry’s <b>"


def test_an_empty_paragraph_has_empty_text():
    assert Paragraph("<w:p/>").text == ""


def test_records_what_stands_between_the_characters_without_adding_to_the_text():
    xml = (
        "<w:p>"
        "<w:r><w:t>one</w:t><w:tab/><w:t>two</w:t></w:r>"
        '<w:r><w:endnoteReference w:id="3"/></w:r>'
        "<w:r><w:t>three</w:t><w:br/></w:r>"
        "<w:r><w:drawing><w:txbxContent><w:p><w:r><w:t>boxed</w:t></w:r></w:p>"
        "</w:txbxContent></w:drawing></w:r>"
        "<w:r><w:lastRenderedPageBreak/><w:t>four</w:t></w:r>"
        '<w:r><w:footnoteReference w:id="2"/></w:r>'
        "</w:p>"
    )
    p = Paragraph(xml)
    assert p.text == "onetwothreefour"
    assert p.barriers == [
        (3, "a tab"),
        (6, "a note marker"),
        (11, "a line break"),
        (11, "a drawing"),
        (15, "a note marker"),
    ]


def test_names_any_other_run_content_and_range_marks_as_barriers():
    xml = (
        "<w:p>"
        '<w:bookmarkStart w:id="1" w:name="here"/>'
        "<w:r><w:t>a</w:t><w:noBreakHyphen/><w:t>b</w:t></w:r>"
        '<w:commentRangeStart w:id="4"/>'
        "<w:r><w:t>c</w:t></w:r>"
        '<w:commentRangeEnd w:id="4"/>'
        '<w:r><w:commentReference w:id="4"/></w:r>'
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        "<w:r><w:instrText>PAGE</w:instrText></w:r>"
        '<w:bookmarkEnd w:id="1"/>'
        "</w:p>"
    )
    p = Paragraph(xml)
    assert p.text == "abc"
    assert p.barriers == [
        (0, "a bookmark"),
        (1, "a special character (w:noBreakHyphen)"),
        (2, "the start or end of a comment's range"),
        (3, "the start or end of a comment's range"),
        (3, "a comment marker"),
        (3, "a field"),
        (3, "a field"),
        (3, "a bookmark"),
    ]


def test_reads_text_inside_a_hyperlink_and_records_where_the_link_starts_and_ends():
    xml = (
        "<w:p><w:r><w:t>see </w:t></w:r>"
        '<w:hyperlink r:id="rId5"><w:r><w:t>the </w:t></w:r><w:r><w:t>site</w:t></w:r></w:hyperlink>'
        "<w:r><w:t> now</w:t></w:r></w:p>"
    )
    p = Paragraph(xml)
    assert p.text == "see the site now"
    assert p.spans == [(4, 12, "a hyperlink")]
    assert p.barriers == []


def test_reads_text_inside_other_wrappers_of_runs():
    xml = (
        "<w:p><w:smartTag><w:r><w:t>one </w:t></w:r></w:smartTag>"
        "<w:sdt><w:sdtPr><w:alias w:val=\"x\"/></w:sdtPr><w:sdtContent>"
        "<w:r><w:t>two </w:t></w:r></w:sdtContent></w:sdt>"
        '<w:fldSimple w:instr="PAGE"><w:r><w:t>3</w:t></w:r></w:fldSimple></w:p>'
    )
    p = Paragraph(xml)
    assert p.text == "one two 3"
    assert p.spans == [
        (0, 4, "a smart tag"),
        (4, 8, "a content control"),
        (8, 9, "a field"),
    ]


def test_reads_the_text_as_it_stands_with_existing_tracked_changes_accepted():
    xml = (
        "<w:p><w:r><w:t>The </w:t></w:r>"
        '<w:ins w:id="0" w:author="A" w:date="2026-01-01T10:00:00Z"><w:r><w:t>quick </w:t></w:r></w:ins>'
        '<w:del w:id="1" w:author="A" w:date="2026-01-01T10:00:00Z">'
        "<w:r><w:delText>slow </w:delText></w:r></w:del>"
        "<w:r><w:t>fox</w:t></w:r>"
        '<w:moveFrom w:id="2" w:author="A"><w:r><w:t>gone </w:t></w:r></w:moveFrom>'
        '<w:moveTo w:id="3" w:author="A"><w:r><w:t> came</w:t></w:r></w:moveTo></w:p>'
    )
    p = Paragraph(xml)
    assert p.text == "The quick fox came"
    assert p.spans == [
        (4, 10, "an existing tracked insertion"),
        (13, 18, "an existing tracked insertion"),
    ]
    assert p.barriers == [
        (10, "an existing tracked deletion"),
        (13, "an existing tracked deletion"),
    ]


def find(xml, needle):
    return Paragraph(xml).find(needle)


def para(*texts):
    return "<w:p>" + "".join(f"<w:r><w:t>{t}</w:t></w:r>" for t in texts) + "</w:p>"


def test_finds_a_phrase_that_word_has_split_across_runs():
    assert find(para("The chat win", "dow is", "n’t where"), "window isn’t") == [(9, 21)]


def test_finds_every_occurrence_including_at_the_very_start_and_end():
    assert find(para("ab ", "cab", " ab"), "ab") == [(0, 2), (4, 6), (7, 9)]


def test_finds_nothing_when_the_phrase_is_absent_or_empty():
    assert find(para("abc"), "abd") == []
    assert find(para("abc"), "") == []


def test_matches_composed_and_decomposed_forms_of_the_same_text():
    nfc, nfd = "café au lait", "café au lait"
    # Offsets are into the paragraph's own text, whichever form it is stored in.
    assert find(para("un ", nfd), "café au") == [(3, 11)]
    assert find(para("un ", nfc), "café au") == [(3, 10)]
    assert find(para("un ", nfd), "café") == [(3, 8)]


def test_does_not_match_a_letter_apart_from_its_accent():
    assert find(para("café"), "cafe") == []
    assert find(para("café"), "cafe") == []


def test_matches_decomposed_hangul_against_composed():
    assert find(para("한글"), "한") == [(0, 3)]


TABBED = "<w:p><w:r><w:t>one</w:t><w:tab/><w:t>two</w:t></w:r></w:p>"
LINKED = (
    "<w:p><w:r><w:t>see </w:t></w:r>"
    '<w:hyperlink r:id="rId5"><w:r><w:t>the site</w:t></w:r></w:hyperlink>'
    "<w:r><w:t> now</w:t></w:r></w:p>"
)
CHANGED = (
    "<w:p><w:r><w:t>The </w:t></w:r>"
    '<w:ins w:id="0" w:author="A"><w:r><w:t>quick </w:t></w:r></w:ins>'
    "<w:r><w:t>brown </w:t></w:r>"
    '<w:del w:id="1" w:author="A"><w:r><w:delText>slow </w:delText></w:r></w:del>'
    "<w:r><w:t>fox</w:t></w:r></w:p>"
)


def test_a_range_is_refused_only_when_a_barrier_is_strictly_inside_it():
    p = Paragraph(TABBED)
    assert p.obstacle(1, 5) == "crosses a tab"
    assert p.obstacle(0, 3) is None  # ends where the tab stands
    assert p.obstacle(3, 6) is None  # starts where the tab stands


def test_a_range_may_sit_inside_a_hyperlink_but_not_cross_its_edge():
    p = Paragraph(LINKED)
    assert p.obstacle(4, 12) is None  # exactly the link's text
    assert p.obstacle(8, 12) is None  # wholly inside
    assert p.obstacle(0, 4) is None  # wholly before
    assert p.obstacle(2, 7) == "crosses the start or end of a hyperlink"
    assert p.obstacle(8, 14) == "crosses the start or end of a hyperlink"
    assert p.obstacle(0, 16) == "crosses the start or end of a hyperlink"


def test_a_range_touching_an_existing_tracked_change_is_refused():
    p = Paragraph(CHANGED)  # reads "The quick brown fox"
    assert p.obstacle(5, 8) == "touches an existing tracked insertion"  # inside it
    assert p.obstacle(2, 6) == "touches an existing tracked insertion"
    assert p.obstacle(0, 4) is None  # ends where the insertion starts
    assert p.obstacle(10, 15) is None  # starts where it ends
    assert p.obstacle(12, 18) == "touches an existing tracked deletion"
    assert p.obstacle(16, 19) is None  # starts where the deletion stands


def test_records_which_note_each_marker_points_to_and_where_it_stands():
    xml = (
        "<w:p><w:r><w:t>One.</w:t></w:r>"
        '<w:r><w:rPr><w:rStyle w:val="EndnoteReference"/></w:rPr><w:endnoteReference w:id="7"/></w:r>'
        "<w:r><w:t> Two</w:t></w:r>"
        '<w:r><w:footnoteReference w:customMarkFollows="1" w:id="2"/></w:r>'
        "<w:r><w:t> three.</w:t></w:r></w:p>"
    )
    assert Paragraph(xml).markers == [(4, "endnote", "7"), (8, "footnote", "2")]
