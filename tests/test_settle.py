import pytest

from booktools.settle import accept, reject

pytestmark = pytest.mark.tier1

S = ' w:author="Claude" w:date="2026-10-03T14:46:00Z"'
OURS = (
    "<w:p><w:r><w:t xml:space=\"preserve\">The </w:t></w:r>"
    f'<w:del w:id="7"{S}><w:r><w:delText>quick</w:delText></w:r>'
    f'<w:proofErr w:type="spellEnd"/><w:r><w:rPr><w:b/></w:rPr><w:delText xml:space="preserve"> red</w:delText></w:r></w:del>'
    f'<w:ins w:id="8"{S}><w:r><w:t>slow</w:t></w:r></w:ins>'
    '<w:r><w:t xml:space="preserve"> fox</w:t></w:r></w:p>'
)


def test_rejecting_restores_the_deleted_runs_and_drops_the_inserted_ones():
    assert reject(OURS, {7, 8}) == (
        "<w:p><w:r><w:t xml:space=\"preserve\">The </w:t></w:r>"
        "<w:r><w:t>quick</w:t></w:r>"
        '<w:proofErr w:type="spellEnd"/><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve"> red</w:t></w:r>'
        '<w:r><w:t xml:space="preserve"> fox</w:t></w:r></w:p>'
    )


def test_accepting_drops_the_deleted_runs_and_keeps_the_inserted_ones():
    assert accept(OURS, {7, 8}) == (
        "<w:p><w:r><w:t xml:space=\"preserve\">The </w:t></w:r>"
        "<w:r><w:t>slow</w:t></w:r>"
        '<w:r><w:t xml:space="preserve"> fox</w:t></w:r></w:p>'
    )


THEIRS = (
    '<w:p><w:pPr><w:rPr><w:ins w:id="1" w:author="Ed"/></w:rPr></w:pPr>'
    '<w:ins w:id="2" w:author="Ed"><w:r><w:t>theirs </w:t></w:r></w:ins>'
    '<w:del w:id="3" w:author="Ed"><w:r><w:delText>gone </w:delText></w:r></w:del>'
    f'<w:ins w:id="8"{S}><w:r><w:t>ours</w:t></w:r></w:ins></w:p>'
)


def test_revisions_not_in_the_set_are_left_exactly_as_they_are():
    untouched = THEIRS[: THEIRS.index('<w:ins w:id="8"')]
    assert reject(THEIRS, {8}) == untouched + "</w:p>"
    assert accept(THEIRS, {8}) == untouched + "<w:r><w:t>ours</w:t></w:r></w:p>"
    assert accept(THEIRS, set()) == THEIRS


def test_an_empty_revision_mark_inside_a_revision_does_not_end_it_early():
    # Word marks an inserted paragraph mark with an empty <w:ins/> inside formatting.
    xml = (
        f'<w:p><w:ins w:id="8"{S}><w:r><w:rPr><w:ins w:id="1" w:author="Ed"/></w:rPr>'
        "<w:t>ours</w:t></w:r></w:ins></w:p>"
    )
    assert reject(xml, {8}) == "<w:p></w:p>"
