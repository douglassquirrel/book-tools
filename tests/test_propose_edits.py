import json
import zipfile
from datetime import datetime, timezone

import pytest

from booktools.propose_edits import main
from tests.docxkit import pack_docx
from tests.samples import SAMPLE_EDITS, sample_parts

pytestmark = pytest.mark.tier2


def clock():
    return datetime(2026, 10, 3, 13, 46, 20, tzinfo=timezone.utc)


class Book:
    """A sample manuscript and edits file in a folder of their own."""

    def __init__(self, tmp_path, edits=SAMPLE_EDITS, parts=None):
        self.folder = tmp_path / "book"
        self.folder.mkdir()
        self.manuscript = self.folder / "in.docx"
        pack_docx(self.manuscript, parts or sample_parts())
        self.edits = self.folder / "edits.json"
        self.edits.write_text(json.dumps(edits), encoding="utf-8")
        self.out = tmp_path / "out" / "new.docx"
        self.out.parent.mkdir()
        self.scratch = tmp_path / "scratch"
        self.scratch.mkdir()

    def run(self, *flags):
        args = [str(self.edits), "--in", str(self.manuscript), "--out", str(self.out)]
        return main(args + ["--tmp", str(self.scratch)] + list(flags), now=clock)


@pytest.fixture
def book(tmp_path):
    return Book(tmp_path)


STAMP = (
    ' w:author="Claude" w:date="2026-10-03T14:46:00Z" w16du:dateUtc="2026-10-03T13:46:00Z"'
)


def test_writes_a_copy_with_the_edits_as_tracked_changes_and_reports_each(book, capsys):
    assert book.run() == 0
    assert capsys.readouterr().out.splitlines() == [
        "E1 | body, paragraph 3 | … at dusk, and the keeper [isn’t → is not]"
        " one to waste oil. | no contractions | PASS",
        "E2 | body, paragraph 4 | … wrote every figure in a [large  →]ledger. | cut | PASS",
        "E3 | Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London]"
        " in the station log. | place | PASS",
        "reject all: PASS: every paragraph reads as in the original",
        "accept all: PASS: the original with exactly the 3 edits made",
        "revisions: PASS: 4 revisions for 3 edits, all by Claude at 2026-10-03T14:46:00Z",
        "package: PASS: 2 parts changed, each well-formed; everything else byte-identical",
        f"wrote {book.out}",
    ]
    with zipfile.ZipFile(book.out) as copy:
        body = copy.read("word/document.xml").decode("utf-8")
    assert (
        f'<w:del w:id="3"{STAMP}><w:r><w:delText>isn’t</w:delText></w:r></w:del>'
        f'<w:ins w:id="4"{STAMP}><w:r><w:t>is not</w:t></w:r></w:ins>' in body
    )


def snapshot(folder):
    return {path.name: path.read_bytes() for path in folder.iterdir()}


def test_the_manuscript_and_its_folder_are_left_exactly_as_they_were(book):
    before = snapshot(book.folder)
    assert book.run() == 0
    assert snapshot(book.folder) == before
    assert list(book.scratch.iterdir()) == []  # the scratch folder was removed


def test_every_entry_but_the_edited_parts_is_byte_identical_in_the_copy(book):
    book.run()
    with zipfile.ZipFile(book.manuscript) as old, zipfile.ZipFile(book.out) as new:
        assert new.namelist() == old.namelist()
        differing = [n for n in old.namelist() if old.read(n) != new.read(n)]
    assert differing == ["word/document.xml", "word/endnotes.xml"]


def test_dry_run_prints_the_same_lines_and_writes_nothing(book, capsys):
    assert book.run("--dry-run") == 0
    assert capsys.readouterr().out.splitlines() == [
        "E1 | body, paragraph 3 | … at dusk, and the keeper [isn’t → is not]"
        " one to waste oil. | no contractions | found",
        "E2 | body, paragraph 4 | … wrote every figure in a [large  →]ledger. | cut | found",
        "E3 | Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London]"
        " in the station log. | place | found",
        f"dry run: 3 edits found; {book.out} would be written; nothing written",
    ]
    assert not book.out.exists()
    assert list(book.scratch.iterdir()) == []


def refused(book, capsys, *flags):
    """Run expecting a refusal to start: exit 2, nothing on stdout, nothing written."""
    existed = book.out.exists()
    assert book.run(*flags) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert book.out.exists() == existed
    return captured.err.splitlines()


def test_refuses_to_start_without_a_usable_edits_file(book, capsys):
    book.edits.unlink()
    assert refused(book, capsys) == [f"propose-edits: {book.edits}: no such file"]
    book.edits.write_text('[{"find": "a", "replace": "a"}, {"fnd": "x"}]')
    assert refused(book, capsys) == [
        f"propose-edits: {book.edits} cannot be used:",
        '  edit 1: "replace" is the same as "find", so the edit would change nothing',
        '  edit 2: unknown key "fnd"',
        '  edit 2: "find" must be text and not empty',
        '  edit 2: "replace" must be text (empty to delete)',
    ]


def test_refuses_to_start_without_a_usable_manuscript(book, capsys):
    book.manuscript.write_text("not a zip")
    assert refused(book, capsys) == [
        f"propose-edits: {book.manuscript}: not a .docx file (it is not a zip archive)"
    ]


def test_refuses_to_write_over_an_existing_file_without_force(book, capsys):
    book.out.write_text("something already here")
    assert refused(book, capsys) == [
        f"propose-edits: {book.out} already exists; give another name or add --force"
    ]
    assert book.out.read_text() == "something already here"
    assert refused(book, capsys, "--dry-run") == [
        f"propose-edits: {book.out} already exists; give another name or add --force"
    ]
    assert book.run("--force") == 0
    assert zipfile.is_zipfile(book.out)


def test_never_writes_over_the_manuscript_even_with_force(book, capsys):
    before = book.manuscript.read_bytes()
    book.out = book.folder / "." / "in.docx"  # the same file by another spelling
    assert refused(book, capsys, "--force") == [
        f"propose-edits: {book.out} is the manuscript itself; a copy must have another name"
    ]
    assert book.manuscript.read_bytes() == before


def test_refuses_when_the_folder_for_the_copy_does_not_exist(book, capsys):
    book.out = book.out.parent / "missing" / "new.docx"
    assert refused(book, capsys) == [
        f"propose-edits: the folder {book.out.parent} does not exist"
    ]


def test_a_usage_error_exits_2_and_help_exits_0(book, capsys):
    assert main(["--in", "x.docx"]) == 2
    assert "usage: propose-edits" in capsys.readouterr().err
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    for flag in ("--in", "--out", "--author", "--dry-run", "--force", "--tmp"):
        assert flag in out


def test_edits_that_cannot_be_placed_exit_1_and_nothing_is_written(tmp_path, capsys):
    edits = [
        {"id": "ok", "find": "March", "replace": "April"},
        {"id": "gone", "find": "no such words", "replace": "x"},
        {"id": "twice", "find": "the", "replace": "a"},
    ]
    book = Book(tmp_path, edits)
    for flags in ((), ("--dry-run",)):
        assert book.run(*flags) == 1
        captured = capsys.readouterr()
        assert captured.out.splitlines() == [
            "ok | body, paragraph 9 | The log for [March → April] is missing. | | found"
        ]
        assert captured.err.splitlines() == [
            "propose-edits: 2 of 3 edits cannot be made; nothing written:",
            '  edit 2 (gone): "find" text not found in the body',
            '  edit 3 (twice): "find" text occurs 2 times in the body (paragraphs 3 and 6);'
            ' add "occurrence" to say which',
        ]
        assert not book.out.exists()


def test_an_empty_edits_file_succeeds_and_writes_no_copy(tmp_path, capsys):
    book = Book(tmp_path, edits=[])
    assert book.run() == 0
    assert capsys.readouterr().out == "no edits, nothing written\n"
    assert not book.out.exists()
