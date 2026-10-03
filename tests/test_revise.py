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


def test_a_pure_deletion_writes_no_insertion():
    xml = "<w:p><w:r><w:t>The big cat</w:t></w:r></w:p>"
    assert revise(Paragraph(xml), Change(4, 8, "", del_id=7), STAMP) == (
        '<w:p><w:r><w:t xml:space="preserve">The </w:t></w:r>'
        + DEL
        + '<w:r><w:delText xml:space="preserve">big </w:delText></w:r></w:del>'
        "<w:r><w:t>cat</w:t></w:r></w:p>"
    )


def test_a_pure_insertion_goes_after_the_character_before_it():
    xml = "<w:p><w:r><w:rPr><w:i/></w:rPr><w:t>The cat</w:t></w:r><w:r><w:t> sat</w:t></w:r></w:p>"
    inserted = INS + '<w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">big </w:t></w:r></w:ins>'
    # In the middle of a run: the run is cut in two around the insertion.
    assert revise(Paragraph(xml), Change(4, 4, "big ", ins_id=8), STAMP) == (
        '<w:p><w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">The </w:t></w:r>'
        + inserted
        + "<w:r><w:rPr><w:i/></w:rPr><w:t>cat</w:t></w:r><w:r><w:t> sat</w:t></w:r></w:p>"
    )
    # At the end of a run: nothing is cut, and the formatting is that run's.
    assert revise(Paragraph(xml), Change(7, 7, "big ", ins_id=8), STAMP) == (
        "<w:p><w:r><w:rPr><w:i/></w:rPr><w:t>The cat</w:t></w:r>"
        + inserted
        + "<w:r><w:t> sat</w:t></w:r></w:p>"
    )


def test_a_pure_insertion_can_go_before_the_character_after_it():
    xml = "<w:p><w:r><w:rPr><w:i/></w:rPr><w:t>The cat</w:t></w:r><w:r><w:t> sat</w:t></w:r></w:p>"
    plain = INS + "<w:r><w:t>,</w:t></w:r></w:ins>"
    assert revise(Paragraph(xml), Change(7, 7, ",", ins_id=8, after=False), STAMP) == (
        "<w:p><w:r><w:rPr><w:i/></w:rPr><w:t>The cat</w:t></w:r>"
        + plain
        + "<w:r><w:t> sat</w:t></w:r></w:p>"
    )
    assert revise(Paragraph(xml), Change(0, 0, "Oh. ", ins_id=8, after=False), STAMP) == (
        "<w:p>"
        + INS
        + '<w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">Oh. </w:t></w:r></w:ins>'
        + "<w:r><w:rPr><w:i/></w:rPr><w:t>The cat</w:t></w:r><w:r><w:t> sat</w:t></w:r></w:p>"
    )


TABBED = (
    "<w:p><w:r><w:rPr><w:b/></w:rPr>"
    "<w:t>one</w:t><w:tab/><w:lastRenderedPageBreak/><w:t>two</w:t><w:tab/><w:t>three</w:t>"
    "</w:r></w:p>"
)


def test_a_run_holding_tabs_is_cut_between_its_children_and_no_tab_is_deleted():
    out = revise(Paragraph(TABBED), Change(3, 6, "2", del_id=7, ins_id=8), STAMP)
    assert out == (
        "<w:p>"
        "<w:r><w:rPr><w:b/></w:rPr><w:t>one</w:t><w:tab/><w:lastRenderedPageBreak/></w:r>"
        + DEL
        + "<w:r><w:rPr><w:b/></w:rPr><w:delText>two</w:delText></w:r></w:del>"
        + INS
        + "<w:r><w:rPr><w:b/></w:rPr><w:t>2</w:t></w:r></w:ins>"
        "<w:r><w:rPr><w:b/></w:rPr><w:tab/><w:t>three</w:t></w:r>"
        "</w:p>"
    )


def test_an_insertion_beside_a_tab_cuts_the_run_on_the_right_side_of_it():
    out = revise(Paragraph(TABBED), Change(3, 3, "!", ins_id=8), STAMP)
    assert out == (
        "<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>one</w:t></w:r>"
        + INS
        + "<w:r><w:rPr><w:b/></w:rPr><w:t>!</w:t></w:r></w:ins>"
        "<w:r><w:rPr><w:b/></w:rPr><w:tab/><w:lastRenderedPageBreak/><w:t>two</w:t><w:tab/>"
        "<w:t>three</w:t></w:r></w:p>"
    )
    out = revise(Paragraph(TABBED), Change(3, 3, "!", ins_id=8, after=False), STAMP)
    assert out == (
        "<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>one</w:t><w:tab/><w:lastRenderedPageBreak/></w:r>"
        + INS
        + "<w:r><w:rPr><w:b/></w:rPr><w:t>!</w:t></w:r></w:ins>"
        "<w:r><w:rPr><w:b/></w:rPr><w:t>two</w:t><w:tab/><w:t>three</w:t></w:r></w:p>"
    )


def test_special_characters_are_escaped_and_entities_are_never_cut_in_two():
    xml = "<w:p><w:r><w:t>Tom &amp; Jerry &lt;3 cheese</w:t></w:r></w:p>"
    out = revise(Paragraph(xml), Change(4, 14, "<&> R", del_id=7, ins_id=8), STAMP)
    assert out == (
        '<w:p><w:r><w:t xml:space="preserve">Tom </w:t></w:r>'
        + DEL
        + "<w:r><w:delText>&amp; Jerry &lt;3</w:delText></w:r></w:del>"
        + INS
        + "<w:r><w:t>&lt;&amp;&gt; R</w:t></w:r></w:ins>"
        '<w:r><w:t xml:space="preserve"> cheese</w:t></w:r></w:p>'
    )


def test_the_stamp_is_written_on_both_revisions_exactly_as_given():
    stamp = ' w:author="A &amp; B" w:date="2026-10-03T14:46:00Z" w16du:dateUtc="2026-10-03T13:46:00Z"'
    xml = "<w:p><w:r><w:t>a b c</w:t></w:r></w:p>"
    out = revise(Paragraph(xml), Change(2, 3, "x", del_id=41, ins_id=42), stamp)
    assert f'<w:del w:id="41"{stamp}>' in out
    assert f'<w:ins w:id="42"{stamp}>' in out


def test_a_change_inside_a_hyperlink_stays_inside_it():
    xml = (
        '<w:p><w:hyperlink r:id="rId5"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'
        "<w:t>the old site</w:t></w:r></w:hyperlink></w:p>"
    )
    out = revise(Paragraph(xml), Change(4, 7, "new", del_id=7, ins_id=8), STAMP)
    link = '<w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'
    assert out == (
        '<w:p><w:hyperlink r:id="rId5">'
        f'<w:r>{link}<w:t xml:space="preserve">the </w:t></w:r>'
        + DEL + f"<w:r>{link}<w:delText>old</w:delText></w:r></w:del>"
        + INS + f"<w:r>{link}<w:t>new</w:t></w:r></w:ins>"
        f'<w:r>{link}<w:t xml:space="preserve"> site</w:t></w:r>'
        "</w:hyperlink></w:p>"
    )
