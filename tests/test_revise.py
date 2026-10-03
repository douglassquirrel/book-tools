import pytest

from booktools.paragraph import Paragraph
from booktools.revise import Change, revise

pytestmark = pytest.mark.tier1

STAMP = ' w:author="Claude" w:date="2026-10-03T14:46:00Z"'
DEL = '<w:del w:id="7"' + STAMP + ">"
INS = '<w:ins w:id="8"' + STAMP + ">"


def test_replaces_words_inside_one_run_keeping_its_formatting_on_every_piece():
    xml = '<w:p><w:r w:rsidR="00AB"><w:rPr><w:b/></w:rPr><w:t>The quick brown fox</w:t></w:r></w:p>'
    out = revise(Paragraph(xml), Change(4, 9, "slow", del_id=7, ins_id=8), STAMP)
    assert out == (
        "<w:p>"
        '<w:r w:rsidR="00AB"><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">The </w:t></w:r>'
        + DEL
        + '<w:r w:rsidR="00AB"><w:rPr><w:b/></w:rPr><w:delText>quick</w:delText></w:r></w:del>'
        + INS
        + "<w:r><w:rPr><w:b/></w:rPr><w:t>slow</w:t></w:r></w:ins>"
        '<w:r w:rsidR="00AB"><w:rPr><w:b/></w:rPr><w:t xml:space="preserve"> brown fox</w:t></w:r>'
        "</w:p>"
    )
