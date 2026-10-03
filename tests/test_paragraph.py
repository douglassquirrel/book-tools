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
