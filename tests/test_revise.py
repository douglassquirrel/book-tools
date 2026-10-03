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


def test_a_change_at_the_very_start_or_end_or_of_the_whole_run_leaves_no_empty_run():
    xml = '<w:p><w:r><w:t xml:space="preserve">One two </w:t></w:r></w:p>'
    change = '<w:ins w:id="8"' + STAMP + "><w:r><w:t>X</w:t></w:r></w:ins>"
    assert revise(Paragraph(xml), Change(0, 3, "X", del_id=7, ins_id=8), STAMP) == (
        "<w:p>" + DEL + "<w:r><w:delText>One</w:delText></w:r></w:del>" + change
        + '<w:r><w:t xml:space="preserve"> two </w:t></w:r></w:p>'
    )
    assert revise(Paragraph(xml), Change(4, 8, "X", del_id=7, ins_id=8), STAMP) == (
        '<w:p><w:r><w:t xml:space="preserve">One </w:t></w:r>'
        + DEL + '<w:r><w:delText xml:space="preserve">two </w:delText></w:r></w:del>' + change
        + "</w:p>"
    )
    # The whole run: nothing is cut, and the text element keeps its own attributes.
    assert revise(Paragraph(xml), Change(0, 8, "X", del_id=7, ins_id=8), STAMP) == (
        "<w:p>" + DEL + '<w:r><w:delText xml:space="preserve">One two </w:delText></w:r></w:del>'
        + change + "</w:p>"
    )


THREE_RUNS = (
    "<w:p>"
    "<w:r><w:t>The qu</w:t></w:r>"
    '<w:proofErr w:type="spellStart"/>'
    "<w:r><w:rPr><w:i/></w:rPr><w:t>ick bro</w:t></w:r>"
    '<w:proofErr w:type="spellEnd"/>'
    '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">wn fox </w:t></w:r>'
    "</w:p>"
)


def test_a_change_across_two_runs_cuts_each_and_takes_the_formatting_of_the_first():
    out = revise(Paragraph(THREE_RUNS), Change(4, 9, "slow", del_id=7, ins_id=8), STAMP)
    assert out == (
        "<w:p>"
        '<w:r><w:t xml:space="preserve">The </w:t></w:r>'
        + DEL
        + "<w:r><w:delText>qu</w:delText></w:r>"
        '<w:proofErr w:type="spellStart"/>'
        "<w:r><w:rPr><w:i/></w:rPr><w:delText>ick</w:delText></w:r></w:del>"
        + INS
        + "<w:r><w:t>slow</w:t></w:r></w:ins>"
        '<w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve"> bro</w:t></w:r>'
        '<w:proofErr w:type="spellEnd"/>'
        '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">wn fox </w:t></w:r>'
        "</w:p>"
    )


def test_a_change_across_three_runs_keeps_each_run_s_own_formatting_in_the_deletion():
    out = revise(Paragraph(THREE_RUNS), Change(6, 15, "ack", del_id=7, ins_id=8), STAMP)
    assert out == (
        "<w:p>"
        "<w:r><w:t>The qu</w:t></w:r>"
        '<w:proofErr w:type="spellStart"/>'
        + DEL
        + "<w:r><w:rPr><w:i/></w:rPr><w:delText>ick bro</w:delText></w:r>"
        '<w:proofErr w:type="spellEnd"/>'
        "<w:r><w:rPr><w:b/></w:rPr><w:delText>wn</w:delText></w:r></w:del>"
        + INS
        + "<w:r><w:rPr><w:i/></w:rPr><w:t>ack</w:t></w:r></w:ins>"
        '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve"> fox </w:t></w:r>'
        "</w:p>"
    )
