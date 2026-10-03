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
