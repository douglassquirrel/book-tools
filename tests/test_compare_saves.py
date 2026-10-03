import hashlib

import pytest

from booktools.compare_saves import main
from tests.docxkit import pack_docx
from tests.samples import edited_parts, sample_parts
from tests.stubs import git_stub, only, pandoc_stub

pytestmark = pytest.mark.tier2


class Saves:
    """Two saves of the sample in a folder, and stand-in pandoc and git on PATH."""

    def __init__(self, tmp_path, monkeypatch):
        self.folder = tmp_path / "book"
        self.folder.mkdir()
        self.old = self.folder / "old.docx"
        self.new = self.folder / "new.docx"
        pack_docx(self.old, sample_parts())
        pack_docx(self.new, edited_parts())
        self.pandoc = pandoc_stub(tmp_path / "pandoc-bin")
        self.git = git_stub(tmp_path / "git-bin")
        self.scratch = tmp_path / "scratch"
        self.scratch.mkdir()
        monkeypatch.setenv("PATH", only(self.pandoc, self.git))

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

    def run(self, *args):
        return main([*args, "--tmp", str(self.scratch)])

    def compare(self, *flags):
        return self.run(str(self.old), str(self.new), *flags)


@pytest.fixture
def saves(tmp_path, monkeypatch):
    return Saves(tmp_path, monkeypatch)


def structure(saves):
    return [
        "== Structure and counts (old | new)",
        f"sha256: {saves.sha(saves.old)} | {saves.sha(saves.new)}",
        "revision: 3 | 4",
        "modified (London time): 2026-10-01 10:00 | 2026-10-02 18:30",
        "parts that differ: word/document.xml, word/endnotes.xml, docProps/core.xml",
        "media: the same 1 file",
        "paragraphs: 9 | 10 (+1)",
        "tracked changes: 0 | 0",
        "trackRevisions: off | off",
        "comments: 0 | 0",
        "endnote markers: 2 | 3 (+1)",
        "endnotes: 2 | 3 (+1)",
        "footnote markers: 1 | 1",
        "footnotes: 1 | 1",
        "straight quotes: 0 | 0",
        "links in notes: 0 | 0",
        "highlighted runs: 0 | 0",
        "notes of more than one paragraph: none | none",
    ]


PARAGRAPHS = [
    "== Paragraph by paragraph",
    "===== word/document.xml paragraphs 9 10",
    "TEXT 2: insert 'The lamp was lit at dusk,' -> '{endnoteReference}The lamp was lit at dawn,'",
    "TEXT 2: replace 'The lamp was lit at dusk, and the keeper isn’t on'"
    " -> 'nce}The lamp was lit at dawn, and the keeper isn’t on'",
    "FORMAT 3: 5 chars, e.g. at 'e every figure in a large ledger.{footno': old[b] new[]",
    "FORMAT 5: 30 chars, e.g. at 'A caption set in ano': old[font=Times-Roman] new[]",
    "PARA-PROPS 6: 'A line at exact spacing.'",
    '   old <w:pPr><w:spacing w:line="280" w:lineRule="exact"/></w:pPr>',
    '   new <w:pPr><w:spacing w:line="300" w:lineRule="exact"/></w:pPr>',
    "ADDED 7: 'A paragraph added in the later save.'",
    "differing paragraphs 5",
    "===== word/endnotes.xml paragraphs 4 5",
    "ADDED 2: ' A note added in the later save.'",
    "differing paragraphs 1",
    "===== word/footnotes.xml paragraphs 3 3",
    "differing paragraphs 0",
]
WORDS = [
    "== Text diff (body and notes, as pandoc reads them)",
    "=== BODY replace",
    "  OLD: The lamp was lit at dusk, and the keeper isn’t one to waste oil.[^1]",
    "  NEW: [^1]The lamp was lit at dawn, and the keeper isn’t one to waste oil.[^2]",
    "=== BODY insert",
    "  NEW: A paragraph added in the later save.",
    "  NEW: ",
    "=== BODY insert",
    "  NEW: ",
    "=== NOTES insert old [] new [1]",
    "  NEW: A note added in the later save.",
]


def test_reports_structure_then_paragraphs_then_words(saves, capsys):
    assert saves.compare() == 0
    assert capsys.readouterr().out.splitlines() == (
        [f"old: {saves.old}", f"new: {saves.new}", ""]
        + structure(saves)
        + [""]
        + PARAGRAPHS
        + [""]
        + WORDS
    )
    assert saves.pandoc.calls() == [
        ["-f", "docx", "-t", "markdown-smart", "--wrap=none", str(saves.old)],
        ["-f", "docx", "-t", "markdown-smart", "--wrap=none", str(saves.new)],
    ]


def snapshot(folder):
    return {path.name: path.read_bytes() for path in folder.iterdir()}


def test_identical_saves_show_no_difference_anywhere(saves, capsys):
    assert saves.run(str(saves.old), str(saves.old)) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[7] == "parts that differ: none"
    assert out[9] == "paragraphs: 9 | 9"
    assert [line for line in out if line.startswith("differing")] == ["differing paragraphs 0"] * 3
    assert out[-2:] == ["== Text diff (body and notes, as pandoc reads them)", "no differences"]


def test_nothing_is_written_beside_the_saves_or_left_in_the_scratch_folder(saves):
    before = snapshot(saves.folder)
    assert saves.compare() == 0
    assert snapshot(saves.folder) == before
    assert list(saves.scratch.iterdir()) == []


def test_a_font_name_to_ignore_is_reported_as_font_name_only(saves, capsys):
    assert saves.compare("--ignore-font", "Arial", "--ignore-font", "Times-Roman") == 0
    out = capsys.readouterr().out.splitlines()
    assert "FONT-NAME-ONLY 5: 30 chars, e.g. at 'A caption set in ano': old[font=Times-Roman] new[]" in out
    assert "FORMAT 3: 5 chars, e.g. at 'e every figure in a large ledger.{footno': old[b] new[]" in out


def test_no_text_diff_leaves_pandoc_out_and_says_so(saves, capsys, monkeypatch, tmp_path):
    empty = tmp_path / "nothing-here"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))  # no pandoc at all
    assert saves.compare("--no-text-diff") == 0
    out = capsys.readouterr().out.splitlines()
    assert out[:3] == [f"old: {saves.old}", f"new: {saves.new}", "text diff left out (--no-text-diff)"]
    assert out[-1] == "differing paragraphs 0"
    assert not any(line.startswith("== Text diff") for line in out)


def test_no_counts_leaves_the_structure_section_out(saves, capsys):
    assert saves.compare("--no-counts") == 0
    out = capsys.readouterr().out.splitlines()
    assert out[:4] == [f"old: {saves.old}", f"new: {saves.new}", "", "== Paragraph by paragraph"]


def test_utc_shows_the_modified_times_in_utc(saves, capsys):
    assert saves.compare("--utc") == 0
    assert "modified (UTC): 2026-10-01 09:00 | 2026-10-02 17:30" in capsys.readouterr().out


def test_refuses_to_start_without_pandoc_and_says_how_to_get_it(saves, capsys, monkeypatch, tmp_path):
    empty = tmp_path / "nothing-here"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert saves.compare() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "compare-saves: pandoc was not found; the text diff needs it. Install it with"
        " `brew install pandoc`, or on a Mac without Homebrew with the installer package"
        " from pandoc.org; or leave the text diff out with --no-text-diff"
    ]


@pytest.mark.parametrize(
    "fault, said",
    [
        ("fail", "pandoc failed on {old}: pandoc: could not read the file"),
        ("silent", "pandoc printed nothing for {old}"),
        ("garbage", "pandoc did not print text for {old}"),
        ("hang", "pandoc did not finish with {old} within 2 seconds"),
    ],
)
def test_a_pandoc_that_fails_still_gives_the_other_sections_and_exits_1(
    saves, capsys, fault, said
):
    saves.pandoc.control(**{fault: True})
    assert saves.compare("--timeout", "2") == 1
    captured = capsys.readouterr()
    out = captured.out.splitlines()
    assert out[-1] == "== Text diff (body and notes, as pandoc reads them)"
    assert "differing paragraphs 5" in out
    assert captured.err.splitlines() == [
        "compare-saves: no text diff: " + said.format(old=saves.old)
    ]


def test_a_save_that_cannot_be_read_exits_1(saves, capsys):
    saves.new.write_text("not a zip")
    assert saves.compare() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        f"compare-saves: {saves.new}: not a .docx file (it is not a zip archive)"
    ]
    assert saves.run(str(saves.old), str(saves.folder / "none.docx")) == 1
    assert capsys.readouterr().err.splitlines() == [
        f"compare-saves: {saves.folder / 'none.docx'}: no such file"
    ]


def test_a_usage_error_exits_2_and_help_exits_0(saves, capsys):
    assert saves.run(str(saves.old)) == 2
    assert capsys.readouterr().err.splitlines() == [
        "compare-saves: give two saves, OLD.docx NEW.docx (or --git OLDREV [NEWREV] FILE.docx)"
    ]
    assert main(["--nonsense"]) == 2
    assert "usage: compare-saves" in capsys.readouterr().err
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    for flag in ("--git", "--ignore-font", "--no-text-diff", "--no-counts", "--utc", "--tmp", "--timeout"):
        assert flag in out
