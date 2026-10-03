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
