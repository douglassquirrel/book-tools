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
