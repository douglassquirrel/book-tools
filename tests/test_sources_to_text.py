import json

import pytest

from booktools.sources_to_text import main
from tests.stubs import FakeImage, only, pandoc_stub, pdf_stubs

pytestmark = pytest.mark.tier2

LONG = "A page with plenty of text on it, far more than eighty characters once spaces are left out."


def pdf(pages, images=None):
    return json.dumps({"pages": pages, "images": images or {}})


class Sources:
    """A folder of invented sources and stand-ins for the programs that read them."""

    def __init__(self, tmp_path, monkeypatch, **control):
        self.folder = tmp_path / "sources"
        self.folder.mkdir()
        self.out = self.folder / "text"
        self.tools = pdf_stubs(tmp_path / "bin", **control)
        self.pandoc = pandoc_stub(tmp_path / "pandoc-bin")
        self.scratch = tmp_path / "scratch"
        self.scratch.mkdir()
        monkeypatch.setenv("PATH", only(self.tools, self.pandoc))

    def add(self, name, content):
        (self.folder / name).write_text(content, encoding="utf-8")

    def run(self, *flags, **more):
        return main([str(self.folder), "--tmp", str(self.scratch), *flags], **more)

    def text(self, name):
        return (self.out / name).read_text(encoding="utf-8")

    def made(self):
        return sorted(path.name for path in self.out.iterdir())


@pytest.fixture
def sources(tmp_path, monkeypatch):
    return Sources(tmp_path, monkeypatch)


def test_converts_each_kind_of_source_smallest_first_and_logs_each(sources, capsys):
    sources.add("b-paper.pdf", pdf([LONG + " One.", LONG + " Two."]))
    sources.add("a-book.epub", "an epub, as far as the stand-in pandoc cares" * 20)
    sources.add("notes.md", "# Notes\n\nKept as they are.\n")
    sources.add("c.txt", "Plain.\n")
    sources.add("talk.mp4", "not a kind that is converted")
    sources.add("SOURCES.md", "the index: never converted")
    sources.add(".DS_Store", "x")
    (sources.folder / "supporting").mkdir()  # folders are not looked into
    (sources.folder / "supporting" / "deep.pdf").write_text(pdf([LONG]))
    assert sources.run() == 0
    assert capsys.readouterr().out.splitlines() == [
        "c.txt: copied",
        "notes.md: copied",
        "talk.mp4: skipped (not a kind this command converts)",
        "b-paper.pdf: 2 pages, 0 read by OCR, 0 turned",
        "a-book.epub: converted with pandoc",
        "4 converted, 1 skipped, 0 failed",
    ]
    assert sources.made() == [
        ".convert-log.txt", "a-book.epub.txt", "b-paper.pdf.txt", "c.txt.txt", "notes.md.txt",
    ]
    assert sources.text("b-paper.pdf.txt") == (
        f"\n=== PDF page 1 of 2 ===\n{LONG} One.\n=== PDF page 2 of 2 ===\n{LONG} Two."
    )
    assert sources.text("notes.md.txt") == "# Notes\n\nKept as they are.\n"
    assert sources.text("a-book.epub.txt") == "plain text of a-book.epub\n"
    assert sources.text(".convert-log.txt").splitlines() == [
        "c.txt txt",
        "notes.md md",
        "SKIP talk.mp4",
        "b-paper.pdf pages=2 ocr=0 turned=0",
        "a-book.epub epub",
    ]
    assert list(sources.scratch.iterdir()) == []
