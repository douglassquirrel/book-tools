import json

import pytest

from booktools.sources_to_text import main
from tests.stubs import FakeImage, only, pandoc_stub, pdf_stubs

pytestmark = pytest.mark.tier2

LONG = (
    "A page with plenty of text on it, a good deal more than eighty characters"
    " once all of the spaces are left out of the count."
)
assert len("".join(LONG.split())) >= 80  # enough not to be sent to OCR


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


SCAN = {
    "pages": [LONG, "", "pg 3", LONG],
    "images": {
        "2": {"text": "Read from the image of page two.", "scores": {"0": 200}},
        "3": {"text": "A table set sideways.", "scores": {"0": 2, "90": 40, "180": 1, "270": 0}},
    },
}


def test_a_page_with_too_little_text_is_read_by_ocr_and_headed_so(sources, capsys):
    sources.add("scan.pdf", json.dumps(SCAN))
    assert sources.run("--no-rotate") == 0
    assert capsys.readouterr().out.splitlines()[0] == "scan.pdf: 4 pages, 2 read by OCR, 0 turned"
    assert sources.text("scan.pdf.txt") == (
        f"\n=== PDF page 1 of 4 ===\n{LONG}"
        "\n=== PDF page 2 of 4 (OCR) ===\nRead from the image of page two."
        "\n=== PDF page 3 of 4 (OCR) ===\nA table set sideways."
        f"\n=== PDF page 4 of 4 ===\n{LONG}"
    )
    assert sources.text(".convert-log.txt") == "scan.pdf pages=4 ocr=2 turned=0\n"
    calls = sources.tools.calls()
    scan = str(sources.folder / "scan.pdf")
    assert calls[0] == ["-layout", scan, "-"]
    assert calls[1][:9] == ["-f", "2", "-l", "2", "-scale-to", "2800", "-gray", "-png", scan]
    assert calls[2][1:] == ["-"]  # tesseract IMAGE -
    assert calls[1][9].startswith(str(sources.scratch))  # the image is made in the scratch folder
    assert list(sources.scratch.iterdir()) == []


def test_a_page_with_no_image_to_read_keeps_what_text_it_had(sources):
    sources.add("thin.pdf", pdf(["short", LONG]))
    assert sources.run() == 0
    assert sources.text("thin.pdf.txt") == (
        f"\n=== PDF page 1 of 2 ===\nshort\n=== PDF page 2 of 2 ===\n{LONG}"
    )


def test_min_chars_and_dpi_scale_can_be_changed(sources):
    sources.add("scan.pdf", json.dumps(SCAN))
    assert sources.run("--min-chars", "3", "--dpi-scale", "1400", "--no-rotate") == 0
    # "pg 3" has three characters that are not spaces: no longer too few, so not read by OCR.
    assert "=== PDF page 3 of 4 ===\npg 3" in sources.text("scan.pdf.txt")
    assert sources.tools.calls()[1][4:6] == ["-scale-to", "1400"]
