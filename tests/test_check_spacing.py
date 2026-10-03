import pytest

from booktools.check_spacing import main
from tests.docxkit import pack_docx
from tests.samples import sample_parts, spaced_parts

pytestmark = pytest.mark.tier2

# The first two parts are, to the letter, what the script this was ported from prints.
TEXT = [
    "== TEXT: 9 paragraphs, 5 double, 4 not double",
    "   by spacing: [('1 lines', 1), ('1.5 lines', 1), ('exact 14 pt', 1), ('atLeast 24 pt', 1)]",
    "   by style: [('Normal', 3), ('Block Quote', 1)]",
]
TEXT_EACH = [
    "   TEXT p3 [The Lighthouse Ledger] Normal | 1 lines | 'Single by its own setting.'",
    "   TEXT p4 [The Lighthouse Ledger] Block Quote | 1.5 lines | 'One and a half by its style.'",
    "   TEXT p5 [The Lighthouse Ledger] Normal | exact 14 pt | [IMG] 'A picture sits in this"
    " paragraph, whose text runs on well past ninety characters so that i'",
    "   TEXT p8 [Chapter 2 has a very long heading that runs p] Normal | atLeast 24 pt |"
    " 'At least 24 points.'",
]
NOTES = [
    "== NOTES: 4 paragraphs, 3 double, 1 not double",
    "   by spacing: [('1 lines', 1)]",
    "   by style: [('Normal', 1)]",
]
NOTES_EACH = ["   NOTES p4 [(start)] Normal | 1 lines | 'Ibid.'"]
FOOTNOTES = [
    "== FOOTNOTES: 3 paragraphs, 2 double, 1 not double",
    "   by spacing: [('exact 10 pt', 1)]",
    "   by style: [('Normal', 1)]",
]
FOOTNOTES_EACH = ["   FOOTNOTES p3 [(start)] Normal | exact 10 pt | 'Imperial pints.'"]


@pytest.fixture
def spaced(tmp_path):
    path = tmp_path / "book" / "Book.docx"
    path.parent.mkdir()
    pack_docx(path, spaced_parts())
    return path


def test_counts_the_paragraphs_not_double_spaced_by_spacing_and_by_style(spaced, capsys):
    assert main([str(spaced)]) == 1
    assert capsys.readouterr().out.splitlines() == TEXT + NOTES + FOOTNOTES


def test_verbose_lists_each_one_with_its_heading_style_spacing_and_text(spaced, capsys):
    assert main([str(spaced), "-v"]) == 1
    assert capsys.readouterr().out.splitlines() == (
        TEXT + TEXT_EACH + NOTES + NOTES_EACH + FOOTNOTES + FOOTNOTES_EACH
    )
