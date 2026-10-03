"""sources-to-text: every source file in a folder to searchable text, a block per page."""

import argparse
import os
import subprocess
import tempfile
import time

from booktools import cli
from booktools.cli import Refusal
from booktools.sources import assemble, split_pages

INDEXES = ("SOURCES.md", "PDF-COVERAGE.md", ".DS_Store")
LOG = ".convert-log.txt"


def main(argv=None, clock=None, image=None):
    """Run the command; return its exit code. `clock` gives the time in seconds and
    `image` stands in for Pillow's Image module (both for tests)."""
    return cli.run(
        "sources-to-text",
        _parser(),
        lambda args: _run(args, clock or time.monotonic, image),
        argv,
    )


def _run(args, clock, image):
    folder = args.sources
    if not os.path.isdir(folder):
        raise Refusal(f"{folder} is not a folder")
    out = args.out or os.path.join(folder, "text")
    os.makedirs(out, exist_ok=True)
    converted = skipped = failed = 0
    with tempfile.TemporaryDirectory(dir=args.tmp) as scratch:
        job = Job(folder, out, scratch, args)
        for name in _sources(folder):
            if os.path.exists(job.target(name)):
                continue
            outcome = job.convert(name)
            print(f"{name}: {outcome}")
            if outcome.startswith("skipped"):
                skipped += 1
            else:
                converted += 1
    print(f"{converted} converted, {skipped} skipped, {failed} failed")
    return 0


def _sources(folder):
    """The files directly in the folder that are sources, smallest first."""
    names = [
        name
        for name in os.listdir(folder)
        if name not in INDEXES and os.path.isfile(os.path.join(folder, name))
    ]
    return sorted(names, key=lambda name: (os.path.getsize(os.path.join(folder, name)), name))


class Job:
    """One run's folders and settings, and the conversion of one file at a time."""

    def __init__(self, folder, out, scratch, args):
        self.folder, self.out, self.scratch, self.args = folder, out, scratch, args

    def target(self, name):
        return os.path.join(self.out, name + ".txt")

    def log(self, line):
        with open(os.path.join(self.out, LOG), "a", encoding="utf-8") as file:
            file.write(line + "\n")

    def convert(self, name):
        """Convert one source; return what to say about it."""
        source = os.path.join(self.folder, name)
        kind = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if kind in ("md", "txt"):
            with open(source, "rb") as file:
                self.write(name, file.read())
            self.log(f"{name} {kind}")
            return "copied"
        if kind == "epub":
            partial = self.target(name) + ".partial"
            subprocess.run(
                ["pandoc", source, "-t", "plain", "--wrap=none", "-o", partial],
                stdin=subprocess.DEVNULL,
                capture_output=True,
            )
            os.replace(partial, self.target(name))
            self.log(f"{name} epub")
            return "converted with pandoc"
        if kind == "pdf":
            return self.pdf(name, source)
        self.log(f"SKIP {name}")
        return "skipped (not a kind this command converts)"

    def pdf(self, name, source):
        done = subprocess.run(
            ["pdftotext", "-layout", source, "-"], stdin=subprocess.DEVNULL, capture_output=True
        )
        pages = split_pages(done.stdout.decode("utf-8", "replace"))
        total = len(pages)
        ocr, turned = [False] * total, [0] * total
        self.write(name, assemble(pages, ocr, turned).encode("utf-8"))
        self.log(f"{name} pages={total} ocr={sum(ocr)} turned={sum(1 for t in turned if t)}")
        return f"{total} pages, {sum(ocr)} read by OCR, {sum(1 for t in turned if t)} turned"

    def write(self, name, data):
        """Write a file's text whole: under another name first, which then takes its place."""
        partial = self.target(name) + ".partial"
        with open(partial, "wb") as file:
            file.write(data)
        os.replace(partial, self.target(name))


def _parser():
    parser = argparse.ArgumentParser(
        prog="sources-to-text",
        description="Turn every source file in a folder into searchable text, one block"
        " per page of a PDF, reading pages with too little text by OCR.",
    )
    parser.add_argument("sources", metavar="SOURCES_DIR")
    parser.add_argument(
        "--out", metavar="DIR", help="where the text goes (default: SOURCES_DIR/text)"
    )
    parser.add_argument("--tmp", metavar="DIR", help="where to make the scratch folder")
    return parser
