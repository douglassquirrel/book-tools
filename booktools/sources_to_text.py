"""sources-to-text: every source file in a folder to searchable text, a block per page."""

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
import time

from booktools import cli
from booktools.cli import Refusal
from booktools.sources import (
    READS_WELL,
    TURNS,
    assemble,
    best_turn,
    needs_ocr,
    pages_that_differ,
    score,
    split_pages,
)

INDEXES = ("SOURCES.md", "PDF-COVERAGE.md", ".DS_Store")
LOG = ".convert-log.txt"
LOCK = ".lock-"


def main(argv=None, clock=None, image=None):
    """Run the command; return its exit code. `clock` gives the time in seconds and
    `image` stands in for Pillow's Image module (both for tests)."""
    given = list(sys.argv[1:] if argv is None else argv)
    return cli.run(
        "sources-to-text",
        _parser(),
        lambda args: _run(args, clock or time.monotonic, image, given),
        argv,
    )


def _run(args, clock, image, given):
    folder = args.sources
    if not os.path.isdir(folder):
        raise Refusal(f"{folder} is not a folder")
    out = args.out or os.path.join(folder, "text")
    for name in args.redo:
        if not os.path.isfile(os.path.join(folder, name)):
            raise Refusal(f"--redo {name}: there is no such file in {folder}")
    os.makedirs(out, exist_ok=True)
    worker = args.worker_report is not None  # one of several processes of a larger run
    if args.clear_locks and not worker:
        for lock in _locks(out):
            os.rmdir(os.path.join(out, lock))
            print(f"cleared the lock {lock}")
    stale = set() if worker else {lock[len(LOCK) :] for lock in _locks(out)}
    if args.no_rotate:
        image = None
    elif image is None:
        image = _pillow()
        if image is None and not worker:
            print(
                "sources-to-text: Pillow is not installed, so each page is read as it stands"
                " and one scanned sideways or upside down will not be noticed"
                " (to install it: python3 -m pip install --user Pillow)",
                file=sys.stderr,
            )
    if args.redo:
        with tempfile.TemporaryDirectory(dir=args.tmp) as scratch:
            return _redo(Job(folder, out, scratch, args, image, clock, None, redo=True))
    deadline = clock() + args.seconds if args.seconds is not None else None
    with tempfile.TemporaryDirectory(dir=args.tmp) as scratch:
        job = Job(folder, out, scratch, args, image, clock, deadline)
        names = [name for name in _sources(folder) if name not in args.skip]
        waiting = [name for name in names if not os.path.exists(job.target(name))]
        if args.workers > 1 and not worker:
            tally = _workers(args.workers, given, scratch)
        else:
            tally = _work(job, waiting)
    if worker:
        with open(args.worker_report, "w", encoding="utf-8") as file:
            json.dump(tally, file)
        return 0
    locked = [name for name in waiting if name in stale and not os.path.exists(job.target(name))]
    settled = set(tally["skipped"]) | set(tally["failed"]) | set(locked)
    unfinished = [
        name for name in waiting if name not in settled and not os.path.exists(job.target(name))
    ]
    summary = (
        f"{len(tally['converted'])} converted, {len(tally['skipped'])} skipped,"
        f" {len(tally['failed'])} failed"
    )
    if unfinished:
        summary += f"; {len(unfinished)} not finished: run again to go on"
    if locked:
        summary += f"; {len(locked)} left locked"
    print(summary)
    for name in locked:
        print(
            f"sources-to-text: {name} is locked ({LOCK}{name}): another run may be working"
            " on it. If none is, run again with --clear-locks",
            file=sys.stderr,
        )
    return 1 if tally["failed"] or locked else 0


def _redo(job):
    """Convert the named files again, each beside its old text, and say what differs.
    The old text is never replaced: that is for the user to decide."""
    names = [name for name in _sources(job.folder) if name in job.args.redo]
    for name in names:
        outcome = job.convert(name)
        old = os.path.join(job.out, name + ".txt")
        new = job.target(name)
        said = f"redone as {os.path.basename(new)}: "
        if name.lower().endswith(".pdf"):
            said += outcome + "; "
        if not os.path.exists(old):
            said += f"there was no {name}.txt to compare it with"
        else:
            with open(old, encoding="utf-8") as was, open(new, encoding="utf-8") as now:
                before, after = was.read(), now.read()
            differ = pages_that_differ(before, after) if name.lower().endswith(".pdf") else None
            if before == after:
                said += f"identical to {name}.txt"
            elif differ:
                pages = ", ".join(str(number) for number in differ)
                said += f"pages that differ from {name}.txt: {pages}"
            else:
                said += f"differs from {name}.txt"
        print(f"{name}: {said}", flush=True)
    print(f"{len(names)} redone, 0 failed")
    return 0


def _work(job, waiting):
    """Convert each waiting file that no other run has claimed; return what became of
    each, by name."""
    tally = {"converted": [], "skipped": [], "failed": []}
    for name in waiting:
        if job.out_of_time():
            break
        lock = os.path.join(job.out, LOCK + name)
        try:
            os.mkdir(lock)
        except FileExistsError:
            continue  # another worker, or another run, has it
        try:
            if os.path.exists(job.target(name)):
                continue  # finished by another worker a moment ago
            try:
                outcome = job.convert(name)
            except OutOfTime as stopped:
                print(f"{name}: {stopped}", flush=True)
                break
            print(f"{name}: {outcome}", flush=True)
            tally["skipped" if outcome.startswith("skipped") else "converted"].append(name)
        finally:
            os.rmdir(lock)
    return tally


def _workers(count, given, scratch):
    """Run `count` processes of this command side by side; they share the work through
    the lock folders. Returns their tallies added together."""
    package = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [package, env.get("PYTHONPATH")]))
    reports = [os.path.join(scratch, f"worker-{number}.json") for number in range(count)]
    running = [
        subprocess.Popen(
            [sys.executable, "-m", "booktools.sources_to_text", *given, "--worker-report", report],
            env=env,
            stdin=subprocess.DEVNULL,
        )
        for report in reports
    ]
    for process in running:
        process.wait()
    tally = {"converted": [], "skipped": [], "failed": []}
    for report in reports:
        if os.path.exists(report):
            with open(report, encoding="utf-8") as file:
                for outcome, names in json.load(file).items():
                    tally[outcome].extend(names)
    # A kind that is not converted is passed over by every worker: count it once.
    tally["skipped"] = sorted(set(tally["skipped"]))
    return tally


def _locks(out):
    """The lock folders now in the output folder."""
    return sorted(
        name
        for name in os.listdir(out)
        if name.startswith(LOCK) and os.path.isdir(os.path.join(out, name))
    )


class OutOfTime(Exception):
    """The time allowed by --seconds ran out part of the way through a file."""


def _pillow():
    """Pillow's Image module if Pillow is installed, else None. It is optional."""
    try:
        from PIL import Image
    except ImportError:
        return None
    return Image


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

    def __init__(self, folder, out, scratch, args, image, clock, deadline, redo=False):
        self.folder, self.out, self.scratch, self.args = folder, out, scratch, args
        self.image = image  # Pillow's Image module, or None to read pages as they are
        self.clock, self.deadline = clock, deadline
        self.redo = redo  # write NAME.txt.new and start afresh, leaving NAME.txt alone

    def out_of_time(self):
        return self.deadline is not None and self.clock() > self.deadline

    def cache(self, name):
        """Where a part-converted PDF's pages are kept between runs."""
        return os.path.join(self.out, f".{name}.pages.json")

    def target(self, name):
        return os.path.join(self.out, name + (".txt.new" if self.redo else ".txt"))

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
        cache = self.cache(name)
        if os.path.exists(cache) and not self.redo:
            with open(cache, encoding="utf-8") as file:
                state = json.load(file)
        else:
            done = subprocess.run(
                ["pdftotext", "-layout", source, "-"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
            )
            pages = split_pages(done.stdout.decode("utf-8", "replace"))
            total = len(pages)
            state = {
                "pages": pages,
                "done": [None] * total,
                "ocr": [False] * total,
                "rot": [0] * total,
            }
        pages, done, ocr, turned = state["pages"], state["done"], state["ocr"], state["rot"]
        total = len(pages)
        for index, page in enumerate(pages):
            if done[index] is not None:
                continue
            if self.out_of_time():
                self.save(cache, state)
                finished = sum(1 for text in done if text is not None)
                raise OutOfTime(
                    f"stopped after {finished} of {total} pages: out of time"
                    f" (--seconds {self.args.seconds:g})"
                )
            if needs_ocr(page, self.args.min_chars):
                read = self.read_image(source, index + 1)
                if read is not None:
                    page, turned[index] = read
                    ocr[index] = True
            done[index] = page
        self.write(name, assemble(done, ocr, turned).encode("utf-8"))
        if os.path.exists(cache) and not self.redo:
            os.remove(cache)
        self.log(f"{name} pages={total} ocr={sum(ocr)} turned={sum(1 for t in turned if t)}")
        return f"{total} pages, {sum(ocr)} read by OCR, {sum(1 for t in turned if t)} turned"

    def save(self, cache, state):
        partial = cache + ".partial"
        with open(partial, "w", encoding="utf-8") as file:
            json.dump(state, file)
        os.replace(partial, cache)

    def read_image(self, source, number):
        """Read one page from its image: (the text, the turn it was read at), or None
        if no image of the page could be made."""
        prefix = os.path.join(self.scratch, "pg")
        subprocess.run(
            ["pdftoppm", "-f", str(number), "-l", str(number), "-scale-to",
             str(self.args.dpi_scale), "-gray", "-png", source, prefix],
            stdin=subprocess.DEVNULL,
            capture_output=True,
        )  # fmt: skip
        images = sorted(glob.glob(prefix + "*.png"))
        if not images:
            return None
        try:
            return self.read_best(images[0])
        finally:
            for image in glob.glob(prefix + "*"):
                os.remove(image)

    def read_best(self, image):
        """Read a page image, turned a quarter or half turn if that reads clearly
        better: (the text, the clockwise turn it was read at)."""
        if self.image is None:
            return self.tesseract(image), 0
        picture = self.image.open(image)
        turned = image + ".rot.png"
        scores = {0: score(self.tesseract(image, "tsv"))}
        if scores[0] < READS_WELL:
            for turn in TURNS:
                picture.rotate(-turn, expand=True).save(turned)
                scores[turn] = score(self.tesseract(turned, "tsv"))
        turn = best_turn(scores)
        if not turn:
            return self.tesseract(image), 0
        picture.rotate(-turn, expand=True).save(turned)
        return self.tesseract(turned), turn

    def tesseract(self, image, *more):
        done = subprocess.run(
            ["tesseract", image, "-", *more], stdin=subprocess.DEVNULL, capture_output=True
        )
        return done.stdout.decode("utf-8", "replace")

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
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        help="how many processes share the work (default 1)",
    )
    parser.add_argument(
        "--clear-locks",
        action="store_true",
        help="remove locks left in the output folder by a run that was killed",
    )
    parser.add_argument("--worker-report", help=argparse.SUPPRESS)
    parser.add_argument(
        "--seconds",
        type=float,
        metavar="S",
        help="stop after about this long; the next run goes on where this one stopped",
    )
    parser.add_argument(
        "--redo",
        nargs="+",
        default=[],
        metavar="FILE",
        help="convert these files again, writing NAME.txt.new beside the old text and"
        " saying which pages differ; the old text is never replaced",
    )
    parser.add_argument(
        "--skip", nargs="+", default=[], metavar="NAME", help="file names to leave alone"
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=80,
        metavar="N",
        help="a page with fewer characters than this, spaces aside, is read by OCR (default 80)",
    )
    parser.add_argument(
        "--dpi-scale",
        type=int,
        default=2800,
        metavar="PIXELS",
        help="the longer side of the page image made for OCR (default 2800)",
    )
    parser.add_argument(
        "--no-rotate", action="store_true", help="read each page as it is; try no turns"
    )
    parser.add_argument("--tmp", metavar="DIR", help="where to make the scratch folder")
    return parser


if __name__ == "__main__":
    sys.exit(main())
