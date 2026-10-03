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
        # Whether or not this machine has Pillow, the tests decide what the command finds.
        monkeypatch.setattr("booktools.sources_to_text._pillow", lambda: None, raising=False)

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


def test_a_page_that_reads_clearly_better_turned_is_read_turned_and_headed_so(sources, capsys):
    sources.add("scan.pdf", json.dumps(SCAN))
    assert sources.run(image=FakeImage) == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines()[0] == "scan.pdf: 4 pages, 2 read by OCR, 1 turned"
    assert captured.err == ""
    assert sources.text("scan.pdf.txt") == (
        f"\n=== PDF page 1 of 4 ===\n{LONG}"
        "\n=== PDF page 2 of 4 (OCR) ===\nRead from the image of page two."
        "\n=== PDF page 3 of 4 (OCR, page turned 90\u00b0 clockwise) ===\n"
        "A table set sideways. [read turned 90]"
        f"\n=== PDF page 4 of 4 ===\n{LONG}"
    )
    assert sources.text(".convert-log.txt") == "scan.pdf pages=4 ocr=2 turned=1\n"
    reads = [call[1:] for call in sources.tools.calls() if call[0].endswith(".png")]
    # Page 2 reads well as it is: scored once, read once. Page 3: scored at each of the
    # four turns, then read at the best.
    assert reads == [["-", "tsv"], ["-"], ["-", "tsv"], ["-", "tsv"], ["-", "tsv"], ["-", "tsv"], ["-"]]
    assert list(sources.scratch.iterdir()) == []


def test_without_pillow_pages_are_read_as_they_are_and_the_run_says_so(sources, capsys):
    sources.add("scan.pdf", json.dumps(SCAN))
    assert sources.run() == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "sources-to-text: Pillow is not installed, so each page is read as it stands and one"
        " scanned sideways or upside down will not be noticed"
        " (to install it: python3 -m pip install --user Pillow)"
    ]
    assert "=== PDF page 3 of 4 (OCR) ===\nA table set sideways." in sources.text("scan.pdf.txt")


def test_no_rotate_tries_no_turns_and_gives_no_warning(sources, capsys):
    sources.add("scan.pdf", json.dumps(SCAN))
    assert sources.run("--no-rotate", image=FakeImage) == 0
    assert capsys.readouterr().err == ""
    assert "(OCR, page turned" not in sources.text("scan.pdf.txt")
    assert not any(call[-1] == "tsv" for call in sources.tools.calls())


class Clock:
    """A clock that moves on a fixed amount each time it is read."""

    def __init__(self, step):
        self.now, self.step = 0.0, step

    def __call__(self):
        self.now += self.step
        return self.now


def test_files_that_already_have_their_text_and_names_to_skip_are_left_alone(sources, capsys):
    sources.add("one.pdf", pdf([LONG]))
    sources.add("two.pdf", pdf([LONG + " Two."]))
    sources.add("three.txt", "Three.")
    assert sources.run("--skip", "two.pdf", "three.txt") == 0
    assert capsys.readouterr().out.splitlines() == [
        "one.pdf: 1 pages, 0 read by OCR, 0 turned",
        "1 converted, 0 skipped, 0 failed",
    ]
    assert sources.run() == 0
    assert capsys.readouterr().out.splitlines() == [
        "three.txt: copied",
        "two.pdf: 1 pages, 0 read by OCR, 0 turned",
        "2 converted, 0 skipped, 0 failed",
    ]
    before = sources.text("one.pdf.txt")
    assert sources.run() == 0
    assert capsys.readouterr().out.splitlines() == ["0 converted, 0 skipped, 0 failed"]
    assert sources.text("one.pdf.txt") == before


def test_out_puts_the_text_in_another_folder(sources, tmp_path):
    sources.add("one.md", "One.")
    elsewhere = tmp_path / "elsewhere"
    assert sources.run("--out", str(elsewhere)) == 0
    assert sorted(path.name for path in elsewhere.iterdir()) == [".convert-log.txt", "one.md.txt"]
    assert [path.name for path in sources.folder.iterdir()] == ["one.md"]


def test_a_run_that_runs_out_of_seconds_stops_and_the_next_run_goes_on_from_the_page_cache(
    sources, capsys
):
    many = {"pages": [""] * 6, "images": {str(n): {"text": f"page {n}"} for n in range(1, 7)}}
    sources.add("scan.pdf", json.dumps(many))
    sources.add("later.txt", "x" * 2000)  # bigger, so it comes after the PDF
    # The clock is read before each page; each reading moves it on by 10 seconds.
    assert sources.run("--no-rotate", "--seconds", "35", clock=Clock(10)) == 0
    assert capsys.readouterr().out.splitlines() == [
        "scan.pdf: stopped after 2 of 6 pages: out of time (--seconds 35)",
        "0 converted, 0 skipped, 0 failed; 2 not finished: run again to go on",
    ]
    assert sources.made() == [".scan.pdf.pages.json"]
    cache = json.loads(sources.text(".scan.pdf.pages.json"))
    assert cache["done"] == ["page 1", "page 2", None, None, None, None]

    ocr_so_far = len([call for call in sources.tools.calls() if call[0].endswith(".png")])
    assert sources.run("--no-rotate") == 0
    assert capsys.readouterr().out.splitlines() == [
        "scan.pdf: 6 pages, 6 read by OCR, 0 turned",
        "later.txt: copied",
        "2 converted, 0 skipped, 0 failed",
    ]
    assert sources.made() == [".convert-log.txt", "later.txt.txt", "scan.pdf.txt"]
    # Pages 1 and 2 were not read a second time, and pdftotext was not run again.
    calls = sources.tools.calls()
    assert len([call for call in calls if call[0].endswith(".png")]) == ocr_so_far + 4
    assert len([call for call in calls if call[0] == "-layout"]) == 1
    assert sources.text("scan.pdf.txt").count("(OCR) ===") == 6


def test_a_lock_left_by_another_run_is_reported_and_its_file_left_alone(sources, capsys):
    sources.add("one.pdf", pdf([LONG]))
    sources.add("two.pdf", pdf([LONG + " Two."]))
    sources.out.mkdir()
    lock = sources.out / ".lock-one.pdf"
    lock.mkdir()
    assert sources.run() == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "two.pdf: 1 pages, 0 read by OCR, 0 turned",
        "1 converted, 0 skipped, 0 failed; 1 left locked",
    ]
    assert captured.err.splitlines()[-1] == (
        "sources-to-text: one.pdf is locked (.lock-one.pdf): another run may be working on it."
        " If none is, run again with --clear-locks"
    )
    assert lock.is_dir() and not (sources.out / "one.pdf.txt").exists()

    assert sources.run("--clear-locks") == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "cleared the lock .lock-one.pdf",
        "one.pdf: 1 pages, 0 read by OCR, 0 turned",
        "1 converted, 0 skipped, 0 failed",
    ]
    assert sources.made() == [".convert-log.txt", "one.pdf.txt", "two.pdf.txt"]  # no lock left


def test_several_workers_convert_every_file_once_between_them(sources, capfd):
    for number in range(1, 7):
        sources.add(f"s{number}.pdf", pdf([LONG + f" Source {number}." * number]))
    assert sources.run("--workers", "3", "--no-rotate") == 0
    out = capfd.readouterr().out.splitlines()  # the workers are processes of their own
    assert sorted(out[:-1]) == [f"s{n}.pdf: 1 pages, 0 read by OCR, 0 turned" for n in range(1, 7)]
    assert out[-1] == "6 converted, 0 skipped, 0 failed"
    assert sources.made() == [".convert-log.txt"] + [f"s{n}.pdf.txt" for n in range(1, 7)]
    # Each file was given to pdftotext exactly once, whichever worker took it.
    given = sorted(call[1] for call in sources.tools.calls() if call[0] == "-layout")
    assert given == sorted(str(sources.folder / f"s{n}.pdf") for n in range(1, 7))
    assert sorted(sources.text(".convert-log.txt").splitlines()) == [
        f"s{n}.pdf pages=1 ocr=0 turned=0" for n in range(1, 7)
    ]
    assert list(sources.scratch.iterdir()) == []


def test_redo_writes_the_new_text_beside_the_old_and_says_which_pages_differ(sources, capsys):
    sources.add("scan.pdf", json.dumps(SCAN))
    sources.add("notes.md", "As it was.\n")
    sources.add("other.pdf", pdf([LONG]))
    assert sources.run("--no-rotate") == 0
    old = sources.text("scan.pdf.txt")
    capsys.readouterr()

    sources.add("notes.md", "As it is now.\n")
    assert sources.run("--redo", "scan.pdf", "notes.md", image=FakeImage) == 0
    assert capsys.readouterr().out.splitlines() == [
        "notes.md: redone as notes.md.txt.new: differs from notes.md.txt",
        "scan.pdf: redone as scan.pdf.txt.new: 4 pages, 2 read by OCR, 1 turned;"
        " pages that differ from scan.pdf.txt: 3",
        "2 redone, 0 failed",
    ]
    assert sources.text("scan.pdf.txt") == old  # the old text is never replaced
    assert sources.text("notes.md.txt") == "As it was.\n"
    assert sources.text("notes.md.txt.new") == "As it is now.\n"
    assert "(OCR, page turned 90° clockwise)" in sources.text("scan.pdf.txt.new")
    assert sources.made() == [
        ".convert-log.txt", "notes.md.txt", "notes.md.txt.new", "other.pdf.txt",
        "scan.pdf.txt", "scan.pdf.txt.new",
    ]


def test_redo_of_an_unchanged_file_says_it_is_identical_and_of_a_new_one_that_there_is_nothing_to_compare(
    sources, capsys
):
    sources.add("same.pdf", pdf([LONG, LONG]))
    assert sources.run() == 0
    sources.add("fresh.txt", "Never converted before.")
    capsys.readouterr()
    assert sources.run("--redo", "same.pdf", "fresh.txt") == 0
    assert capsys.readouterr().out.splitlines() == [
        "fresh.txt: redone as fresh.txt.txt.new: there was no fresh.txt.txt to compare it with",
        "same.pdf: redone as same.pdf.txt.new: 2 pages, 0 read by OCR, 0 turned;"
        " identical to same.pdf.txt",
        "2 redone, 0 failed",
    ]
    assert not (sources.out / "fresh.txt.txt").exists()


def test_redo_of_a_name_that_is_not_a_source_is_refused(sources, capsys):
    sources.add("one.pdf", pdf([LONG]))
    assert sources.run("--redo", "one.pdf", "nine.pdf") == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        f"sources-to-text: --redo nine.pdf: there is no such file in {sources.folder}"
    )
    assert not sources.out.exists() or sources.made() == []


def test_a_file_that_fails_is_reported_and_the_run_goes_on_and_exits_1(sources, capsys):
    sources.add("a-good.pdf", pdf([LONG]))
    sources.add("b-bad.pdf", pdf([LONG, LONG]))
    sources.add("c-also-good.pdf", pdf([LONG, LONG, LONG]))
    sources.tools.control(fail_on=["pdftotext -layout " + str(sources.folder / "b-bad.pdf")])
    assert sources.run() == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "a-good.pdf: 1 pages, 0 read by OCR, 0 turned",
        "b-bad.pdf: FAILED: pdftotext failed: stand-in: could not read the file",
        "c-also-good.pdf: 3 pages, 0 read by OCR, 0 turned",
        "2 converted, 0 skipped, 1 failed",
    ]
    assert sources.made() == [".convert-log.txt", "a-good.pdf.txt", "c-also-good.pdf.txt"]
    assert sources.text(".convert-log.txt").splitlines()[1] == (
        "FAILED b-bad.pdf: pdftotext failed: stand-in: could not read the file"
    )


@pytest.mark.parametrize(
    "control, said",
    [
        ({"silent_on": ["pdftotext"]}, "pdftotext printed nothing"),
        ({"hang_on": ["pdftotext"]}, "pdftotext did not finish within 2 seconds"),
        ({"fail_on": ["pdftoppm"]}, "page 2: pdftoppm failed: stand-in: could not read the file"),
        ({"hang_on": ["pdftoppm"]}, "page 2: pdftoppm did not finish within 2 seconds"),
        ({"fail_on": ["tesseract"]}, "page 2: tesseract failed: stand-in: could not read the file"),
        ({"hang_on": ["tesseract"]}, "page 2: tesseract did not finish within 3 seconds"),
    ],
)
def test_each_way_a_program_can_fail_on_a_pdf(sources, capsys, control, said):
    sources.add("scan.pdf", json.dumps(SCAN))
    sources.tools.control(**control)
    assert sources.run("--no-rotate", "--timeout", "2", "--ocr-timeout", "3") == 1
    assert capsys.readouterr().out.splitlines() == [
        f"scan.pdf: FAILED: {said}",
        "0 converted, 0 skipped, 1 failed",
    ]
    assert not (sources.out / "scan.pdf.txt").exists()
    assert not [name for name in sources.made() if "partial" in name or "lock" in name]
    assert list(sources.scratch.iterdir()) == []


def test_bytes_that_are_not_text_are_kept_as_replacement_characters_not_a_failure(sources):
    sources.add("odd.pdf", pdf([LONG]))
    sources.tools.control(garbage_on=["pdftotext"])
    assert sources.run() == 0
    assert sources.text("odd.pdf.txt").startswith("\n=== PDF page 1 of 1 ===\n�� not text")


def test_an_epub_pandoc_cannot_read_fails_without_leaving_anything(sources, capsys):
    sources.add("book.epub", "x")
    sources.pandoc.control(fail=True)
    assert sources.run() == 1
    assert capsys.readouterr().out.splitlines()[0] == (
        "book.epub: FAILED: pandoc failed: pandoc: could not read the file"
    )
    assert sources.made() == [".convert-log.txt"]


def test_a_failure_part_way_through_a_pdf_keeps_the_pages_done_for_the_next_run(sources, capsys):
    many = {"pages": [""] * 3, "images": {str(n): {"text": f"page {n}"} for n in range(1, 4)}}
    sources.add("scan.pdf", json.dumps(many))
    sources.tools.control(fail_on=["-f 3 "])  # pdftoppm fails on the third page
    assert sources.run("--no-rotate") == 1
    assert json.loads(sources.text(".scan.pdf.pages.json"))["done"] == ["page 1", "page 2", None]
    sources.tools.control()
    capsys.readouterr()
    assert sources.run("--no-rotate") == 0
    assert capsys.readouterr().out.splitlines()[0] == "scan.pdf: 3 pages, 3 read by OCR, 0 turned"
    assert sources.made() == [".convert-log.txt", "scan.pdf.txt"]


def test_refuses_to_start_when_a_needed_program_is_missing_and_names_it(sources, capsys, monkeypatch, tmp_path):
    empty = tmp_path / "nothing-here"
    empty.mkdir()
    sources.add("paper.pdf", pdf([LONG]))
    sources.add("book.epub", "x")
    monkeypatch.setenv("PATH", str(empty))
    assert sources.run() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines()[-1] == (
        "sources-to-text: not found: pdftotext, pdftoppm, tesseract, pandoc."
        " Install them with: brew install poppler tesseract pandoc"
        " (pdftotext and pdftoppm come with poppler)"
    )
    assert not sources.out.exists()
    monkeypatch.setenv("PATH", only(sources.tools))  # everything but pandoc
    assert sources.run() == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        "sources-to-text: not found: pandoc. Install it with: brew install pandoc"
    )


def test_a_program_is_needed_only_if_a_file_waiting_needs_it(sources, capsys, monkeypatch, tmp_path):
    empty = tmp_path / "nothing-here"
    empty.mkdir()
    sources.add("notes.md", "Only a note.")
    monkeypatch.setenv("PATH", str(empty))
    assert sources.run() == 0
    assert capsys.readouterr().out.splitlines()[0] == "notes.md: copied"


def test_refusals_and_help(sources, capsys, tmp_path):
    assert main([str(tmp_path / "no-such-folder")]) == 2
    assert capsys.readouterr().err.splitlines() == [
        f"sources-to-text: {tmp_path / 'no-such-folder'} is not a folder"
    ]
    a_file = tmp_path / "a-file"
    a_file.write_text("x")
    assert sources.run("--out", str(a_file)) == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        f"sources-to-text: --out {a_file} is a file, not a folder"
    )
    assert sources.run("--workers", "0") == 2
    assert capsys.readouterr().err.splitlines()[-1] == "sources-to-text: --workers must be 1 or more"
    assert main([]) == 2
    assert "usage: sources-to-text" in capsys.readouterr().err
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    for flag in ("SOURCES_DIR", "--out", "--workers", "--seconds", "--min-chars", "--dpi-scale",
                 "--no-rotate", "--redo", "--skip", "--clear-locks", "--tmp", "--timeout",
                 "--ocr-timeout"):
        assert flag in out
    assert "--worker-report" not in out


def test_an_interrupted_run_leaves_no_lock_no_part_written_text_and_no_scratch(
    sources, capsys, monkeypatch
):
    import booktools.sources_to_text as command

    sources.add("one.pdf", pdf([LONG]))

    def interrupt(self, name, data):
        with open(self.target(name) + ".partial", "wb") as file:
            file.write(b"half")
        raise KeyboardInterrupt

    monkeypatch.setattr(command.Job, "write", interrupt)
    assert sources.run() == 130
    assert capsys.readouterr().err.splitlines()[-1] == (
        "sources-to-text: interrupted; run again to go on from where it stopped"
    )
    assert sources.made() == []
    assert list(sources.scratch.iterdir()) == []
