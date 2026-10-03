import hashlib
import json

import pytest

from booktools.note_map import main
from tests.docxkit import pack_docx
from tests.samples import edited_parts, sample_parts

pytestmark = pytest.mark.tier2


class Book:
    """A manuscript in a folder of its own, a registry elsewhere, and saves to make."""

    def __init__(self, tmp_path):
        self.folder = tmp_path / "book"
        self.folder.mkdir()
        self.manuscript = self.folder / "Book.docx"
        self.records = tmp_path / "records"
        self.records.mkdir()
        self.registry = self.records / "notes.json"
        self.map = self.records / "note-map.md"
        self.save(sample_parts())

    def save(self, parts):
        pack_docx(self.manuscript, parts)
        return hashlib.sha256(self.manuscript.read_bytes()).hexdigest()

    def run(self, *flags):
        return main([str(self.manuscript), "--registry", str(self.registry), *flags])

    def ids(self):
        notes = json.loads(self.registry.read_text(encoding="utf-8"))["notes"]
        return [(n["id"], n["kind"], n["text"][:14], n["retired_in"] is not None) for n in notes]


@pytest.fixture
def book(tmp_path):
    return Book(tmp_path)


def test_a_first_run_gives_every_note_an_id_and_prints_the_map(book, capsys):
    assert book.run() == 0
    assert capsys.readouterr().out.splitlines() == [
        "3 notes: 0 carried, 3 new, 0 retired",
        "new: N-0001 endnote:1 Recorded by Trinity House in the station",
        "new: N-0002 endnote:2 Ibid.",
        "new: N-0003 footnote:1 Imperial pints.",
        "N-0001 | endnote:1 | Chapter 1, note 1 | Recorded by Trinity House in the station",
        "N-0002 | endnote:2 | Chapter 2, note 2 | Ibid.",
        "N-0003 | footnote:1 | Chapter 1, note 1 | Imperial pints.",
    ]
    assert book.ids() == [
        ("N-0001", "endnote", "Recorded by Tr", False),
        ("N-0002", "endnote", "Ibid.", False),
        ("N-0003", "footnote", "Imperial pints", False),
    ]


def test_an_unchanged_save_changes_nothing_in_the_registry(book, capsys):
    book.run()
    before = book.registry.read_bytes()
    assert book.run() == 0
    assert capsys.readouterr().out.splitlines()[-4:] == [
        "3 notes: 3 carried, 0 new, 0 retired",
        "N-0001 | endnote:1 | Chapter 1, note 1 | Recorded by Trinity House in the station",
        "N-0002 | endnote:2 | Chapter 2, note 2 | Ibid.",
        "N-0003 | footnote:1 | Chapter 1, note 1 | Imperial pints.",
    ]
    assert book.registry.read_bytes() == before


def test_a_later_save_carries_every_id_though_every_number_moved(book, capsys):
    book.run()
    capsys.readouterr()
    book.save(edited_parts())  # a note added in front of the others, and a word changed
    assert book.run() == 0
    assert capsys.readouterr().out.splitlines() == [
        "4 notes: 3 carried, 1 new, 0 retired",
        "new: N-0004 endnote:1 A note added in the later save.",
        "N-0004 | endnote:1 | Chapter 1, note 1 | A note added in the later save.",
        "N-0001 | endnote:2 | Chapter 1, note 2 | Recorded by Trinity House in the station",
        "N-0002 | endnote:3 | Chapter 2, note 3 | Ibid.",
        "N-0003 | footnote:1 | Chapter 1, note 1 | Imperial pints.",
    ]


def test_a_deleted_note_is_retired_and_stays_in_the_registry(book, capsys):
    book.save(edited_parts())
    book.run()
    capsys.readouterr()
    book.save(sample_parts())  # the added note is gone again
    assert book.run() == 0
    out = capsys.readouterr().out.splitlines()
    assert out[:2] == [
        "3 notes: 3 carried, 0 new, 1 retired",
        "retired: N-0001 A note added in the later save.",
    ]
    assert out[-1] == "retired: N-0001"
    assert book.ids()[-1] == ("N-0001", "endnote", "A note added i", True)


def test_the_manuscript_is_only_read_and_nothing_else_appears_beside_it_or_the_registry(book):
    before = book.manuscript.read_bytes()
    book.run()
    book.run()
    assert book.manuscript.read_bytes() == before
    assert [path.name for path in book.folder.iterdir()] == ["Book.docx"]
    assert [path.name for path in book.records.iterdir()] == ["notes.json"]  # no .prev, no partial


def moved_and_rewritten():
    """A save in which the first endnote was reworded and its sentence recast."""
    parts = sample_parts()
    parts["word/document.xml"] = parts["word/document.xml"].replace(
        "The lamp was lit at dusk, and the kee", "At dusk the lamp was always lit; the kee"
    )
    parts["word/endnotes.xml"] = parts["word/endnotes.xml"].replace(
        "Recorded by Trinity House in the station log.",
        "The station log, as recorded by Trinity House.",
    )
    return parts


def test_an_unclear_note_is_listed_with_its_candidates_and_nothing_is_written(book, capsys):
    book.run()
    before = book.registry.read_bytes()
    capsys.readouterr()
    book.save(moved_and_rewritten())
    assert book.run("--map", str(book.map)) == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        'unclear: endnote:1 "The station log, as recorded by Trinity " in the sentence'
        ' "At dusk the lamp was always lit; the keeper isn’t one to waste oil."',
        '  if it is N-0001 "Recorded by Trinity House in the station": --assign N-0001=endnote:1',
        "  if it is a new note: --assign new=endnote:1",
    ]
    assert captured.err.splitlines() == [
        "note-map: 1 note is unclear and was not guessed; nothing written."
        " Run again with --assign for each"
    ]
    assert book.registry.read_bytes() == before
    assert not book.map.exists()


def test_assign_settles_it_either_way(book, capsys):
    book.run()
    book.save(moved_and_rewritten())
    assert book.run("--assign", "N-0001=endnote:1") == 0
    assert capsys.readouterr().out.splitlines()[-4] == "3 notes: 3 carried, 0 new, 0 retired"
    assert book.ids()[0] == ("N-0001", "endnote", "The station lo", False)

    book.save(sample_parts())  # back to the old wording: unclear again
    assert book.run() == 1
    capsys.readouterr()
    assert book.run("--assign", "new=1") == 2  # a bare number is refused: two kinds of note
    assert capsys.readouterr().err.splitlines() == [
        "note-map: --assign new=1: say endnote:1 or footnote:1, since this document has both"
    ]
    assert book.run("--assign", "new=endnote:1") == 0
    assert capsys.readouterr().out.splitlines()[:3] == [
        "3 notes: 2 carried, 1 new, 1 retired",
        "new: N-0004 endnote:1 Recorded by Trinity House in the station",
        "retired: N-0001 The station log, as recorded by Trinity ",
    ]


def test_an_assignment_that_makes_no_sense_is_a_refusal(book, capsys):
    book.run()
    capsys.readouterr()
    for flag, message in (
        ("N-0009=endnote:1", "--assign N-0009=endnote:1: N-0009 is not a live ID in the registry"),
        ("N-0001=endnote:7", "--assign N-0001=endnote:7: there is no endnote:7 in this save"
                             " (it has 2 endnotes)"),
        ("N-0001", "--assign N-0001: must be ID=NUMBER or new=NUMBER,"
                   " NUMBER being endnote:N or footnote:N"),
        ("N-0001=endnote:x", "--assign N-0001=endnote:x: must be ID=NUMBER or new=NUMBER,"
                             " NUMBER being endnote:N or footnote:N"),
    ):
        assert book.run("--assign", flag) == 2
        assert capsys.readouterr().err.splitlines() == [f"note-map: {message}"]


def test_the_map_file_is_made_afresh_and_the_map_is_then_not_printed(book, capsys):
    book.map.write_text("something stale")
    assert book.run("--map", str(book.map)) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "new: N-0003 footnote:1 Imperial pints."
    text = book.map.read_text(encoding="utf-8")
    assert text.startswith("# Note map\n\nMade by note-map from `Book.docx` (SHA-256 `")
    assert "| N-0002 | Ibid. | endnote:2 | 2 | Chapter 2 |\n" in text
    assert text.endswith("\nRetired: none.\n")


def test_dry_run_reports_what_would_change_and_writes_nothing(book, capsys):
    assert book.run("--dry-run", "--map", str(book.map)) == 0
    assert capsys.readouterr().out.splitlines() == [
        "dry run: 3 notes: 0 carried, 3 new, 0 retired; nothing written",
        "new: N-0001 endnote:1 Recorded by Trinity House in the station",
        "new: N-0002 endnote:2 Ibid.",
        "new: N-0003 footnote:1 Imperial pints.",
    ]
    assert not book.registry.exists() and not book.map.exists()


def refused(book, capsys, *flags):
    assert book.run(*flags) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    return captured.err.splitlines()


def test_refuses_a_missing_manuscript_a_damaged_registry_and_missing_folders(book, capsys):
    book.registry.write_text("{}")
    assert refused(book, capsys) == [
        f"note-map: {book.registry} cannot be used: it is not a note registry written by note-map"
    ]
    assert book.registry.read_text() == "{}"
    book.registry.unlink()
    elsewhere = book.records / "missing" / "notes.json"
    assert book.run("--registry", str(elsewhere)) == 2
    assert capsys.readouterr().err.splitlines() == [
        f"note-map: the folder {elsewhere.parent} does not exist"
    ]
    assert refused(book, capsys, "--map", str(book.records / "missing" / "map.md")) == [
        f"note-map: the folder {book.records / 'missing'} does not exist"
    ]
    assert refused(book, capsys, "--map", str(book.manuscript)) == [
        f"note-map: {book.manuscript} is the manuscript itself; give the map another name"
    ]
    book.manuscript.unlink()
    assert refused(book, capsys) == [f"note-map: {book.manuscript}: no such file"]


def test_a_usage_error_exits_2_and_help_exits_0(capsys):
    assert main(["--registry", "x"]) == 2
    assert "usage: note-map" in capsys.readouterr().err
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    for flag in ("MANUSCRIPT.docx", "--registry", "--map", "--assign", "--dry-run"):
        assert flag in out


def test_a_document_with_no_notes_gives_an_empty_registry(tmp_path, capsys):
    from tests.samples import W

    book = Book(tmp_path)
    book.save({"word/document.xml": f"<w:document {W}><w:body><w:p/></w:body></w:document>"})
    assert book.run() == 0
    assert capsys.readouterr().out == "0 notes: 0 carried, 0 new, 0 retired\n"
    assert book.ids() == []
