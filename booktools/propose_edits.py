"""propose-edits: write a copy of a .docx with a list of edits in it as tracked changes."""

import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

from booktools.clock import instant, revision_dates
from booktools.docx import Docx, DocxError
from booktools.editsfile import EditsFileError, parse_edits
from booktools.manuscript import Manuscript
from booktools.plan import PlanError, plan
from booktools.propose import apply, highest_id, verify
from booktools.report import edit_line


class Refusal(Exception):
    """The command will not start. `lines` say why, the first being the headline."""

    def __init__(self, *lines):
        super().__init__(lines[0])
        self.lines = lines


def main(argv=None, now=None):
    """Run the command; return its exit code. `now` gives the current time (for tests)."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as stop:
        return stop.code
    try:
        return _run(args, now or (lambda: datetime.now(timezone.utc)))
    except Refusal as refusal:
        print(f"propose-edits: {refusal.lines[0]}", file=sys.stderr)
        for line in refusal.lines[1:]:
            print(f"  {line}", file=sys.stderr)
        return 2


def _run(args, now):
    try:
        when = instant(args.date, utc=args.utc) if args.date else now()
    except ValueError:
        raise Refusal(
            "--date must be like 2026-10-03T14:46 (London time, or UTC with --utc),"
            " or carry an offset such as +01:00 or Z"
        ) from None
    try:
        with open(args.edits, encoding="utf-8") as file:
            edits = parse_edits(file.read())
    except FileNotFoundError:
        raise Refusal(f"{args.edits}: no such file") from None
    except EditsFileError as error:
        raise Refusal(f"{args.edits} cannot be used:", *error.problems) from None
    try:
        docx = Docx(args.manuscript)
    except DocxError as error:
        raise Refusal(str(error)) from None
    if os.path.realpath(args.out) == os.path.realpath(args.manuscript):
        raise Refusal(f"{args.out} is the manuscript itself; a copy must have another name")
    folder = os.path.dirname(args.out) or "."
    if not os.path.isdir(folder):
        raise Refusal(f"the folder {folder} does not exist")
    if os.path.exists(args.out) and not args.force:
        raise Refusal(f"{args.out} already exists; give another name or add --force")
    parts = docx.texts()
    manuscript = Manuscript(parts)
    if not edits:
        print("no edits, nothing written")
        return 0
    try:
        located = plan(edits, manuscript, highest_id(parts))
    except PlanError as error:
        for found in error.located:
            print(edit_line(found, found.text, _place(manuscript, found), "found"))
        failed = len(edits) - len(error.located)
        headline = f"{failed} of {_count(len(edits), 'edit')} cannot be made; nothing written:"
        print(f"propose-edits: {headline}", file=sys.stderr)
        for problem in error.problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    if args.dry_run:
        for found in located:
            print(edit_line(found, found.text, _place(manuscript, found), "found"))
        print(f"dry run: {_count(len(located), 'edit')} found; {args.out} would be written; nothing written")
        return 0
    dates = revision_dates(when, utc=args.utc)
    out = apply(parts, located, args.author, dates)
    changed = {name: text for name, text in out.items() if text != parts[name]}
    with tempfile.TemporaryDirectory(dir=args.tmp) as scratch:
        copy = os.path.join(scratch, "copy.docx")
        docx.write_copy(copy, changed)
        results = verify(parts, Docx(copy).texts(), located, args.author, dates)
        for found in located:
            print(edit_line(found, found.text, _place(manuscript, found), "PASS"))
        for name, passed, detail in results:
            print(f"{name}: {'PASS' if passed else 'FAIL'}: {detail}")
        shutil.move(copy, args.out)
    print(f"wrote {args.out}")
    return 0


def _count(number, noun):
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _place(manuscript, found):
    """Where an edit is, in the author's terms."""
    target = found.target
    if target.place == "body":
        return f"body, paragraph {target.number}"
    kind, _, number = target.place.partition(":")
    return manuscript.note_label(kind, int(number))


def _parser():
    parser = argparse.ArgumentParser(
        prog="propose-edits",
        description="Write a copy of a .docx with a list of edits in it as tracked changes."
        " The manuscript itself is only read.",
    )
    parser.add_argument("edits", metavar="EDITS.json", help="the edits file: a JSON list")
    parser.add_argument("--in", dest="manuscript", required=True, metavar="MANUSCRIPT.docx")
    parser.add_argument("--out", required=True, metavar="NEW.docx", help="the copy to write")
    parser.add_argument("--author", default="Claude", metavar="NAME")
    parser.add_argument(
        "--date", metavar="ISO", help="the date and time to put on the changes (default: now)"
    )
    parser.add_argument(
        "--utc", action="store_true", help="write dates in UTC instead of London time"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="show where each edit falls and write nothing"
    )
    parser.add_argument(
        "--force", action="store_true", help="write the copy even if a file of that name exists"
    )
    parser.add_argument("--tmp", metavar="DIR", help="where to make the scratch folder")
    return parser
