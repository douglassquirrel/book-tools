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
