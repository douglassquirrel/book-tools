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


def book(tmp_path, parts):
    path = tmp_path / "Book.docx"
    pack_docx(path, parts)
    return path


def all_double():
    """The sample without its one exact-spaced paragraph."""
    from tests.samples import BODY_PARAGRAPHS

    return sample_parts([p for p in BODY_PARAGRAPHS if "exact" not in p])


def test_exits_0_when_every_paragraph_matches_and_1_when_any_does_not(tmp_path, capsys):
    assert main([str(book(tmp_path, all_double()))]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "== TEXT: 8 paragraphs, 8 double, 0 not double"
    assert main([str(book(tmp_path, sample_parts()))]) == 1
    assert capsys.readouterr().out.splitlines()[0] == "== TEXT: 9 paragraphs, 8 double, 1 not double"


def test_expect_single_or_a_number_changes_what_counts(spaced, capsys):
    assert main([str(spaced), "--expect", "single"]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "== TEXT: 9 paragraphs, 1 single, 8 not single"
    assert out[3] == "== NOTES: 4 paragraphs, 1 single, 3 not single"
    assert main([str(spaced), "--expect", "360"]) == 1
    assert capsys.readouterr().out.splitlines()[0] == (
        "== TEXT: 9 paragraphs, 1 at 1.5 lines, 8 not at 1.5 lines"
    )
    assert main([str(spaced), "--expect", "double"]) == 1
    assert capsys.readouterr().out.splitlines()[0] == TEXT[0]


def test_a_document_with_nothing_set_anywhere_is_single_spaced(tmp_path, capsys):
    from tests.samples import W

    parts = {
        "word/document.xml": f"<w:document {W}><w:body><w:p><w:r><w:t>Bare.</w:t></w:r></w:p>"
        "</w:body></w:document>",
    }
    path = book(tmp_path, parts)  # not even a styles part
    assert main([str(path), "--expect", "single"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "== TEXT: 1 paragraphs, 1 single, 0 not single",
        "   by spacing: []",
        "   by style: []",
    ]
    assert main([str(path)]) == 1
    assert capsys.readouterr().out.splitlines()[1] == "   by spacing: [('single (unset)', 1)]"


def test_refusals_and_help(tmp_path, capsys, spaced):
    assert main([str(tmp_path / "none.docx")]) == 2
    assert capsys.readouterr().err.splitlines() == [
        f"check-spacing: {tmp_path / 'none.docx'}: no such file"
    ]
    for bad in ("triple", "0", "-5", "1.5"):
        assert main([str(spaced), "--expect", bad]) == 2
        assert capsys.readouterr().err.splitlines() == [
            "check-spacing: --expect must be double, single, or a whole number of 240ths"
            " of a line (360 is one and a half)"
        ]
    assert main([]) == 2
    assert "usage: check-spacing" in capsys.readouterr().err
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "--expect" in out and "-v" in out


def test_the_manuscript_is_only_read(spaced):
    before = {path.name: path.read_bytes() for path in spaced.parent.iterdir()}
    main([str(spaced), "-v"])
    assert {path.name: path.read_bytes() for path in spaced.parent.iterdir()} == before
