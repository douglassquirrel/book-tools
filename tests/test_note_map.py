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
