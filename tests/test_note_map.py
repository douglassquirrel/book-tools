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
