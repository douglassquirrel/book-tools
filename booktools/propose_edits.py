"""propose-edits: write a copy of a .docx with a list of edits in it as tracked changes."""

import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

from booktools import cli
from booktools.cli import Refusal
from booktools.clock import instant, revision_dates
from booktools.docx import Docx, DocxError
from booktools.editsfile import EditsFileError, parse_edits
from booktools.manuscript import Manuscript
from booktools.notes import read_notes
from booktools.plan import PlanError, plan
from booktools.propose import apply, edit_results, highest_id, verify
from booktools.registry import RegistryError, load_registry, where_now
from booktools.report import ARROW, edit_line


def main(argv=None, now=None):
    """Run the command; return its exit code. `now` gives the current time (for tests)."""
    now = now or (lambda: datetime.now(timezone.utc))
    return cli.run(
        "propose-edits",
        _parser(),
        lambda args: _run(args, now),
        argv,
        interrupted="interrupted; nothing written",
    )


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
    if args.registry and os.path.realpath(args.out) == os.path.realpath(args.registry):
        raise Refusal(f"{args.out} is the registry; a copy must have another name")
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
    ids = _ids(edits, manuscript, args.registry)
    try:
        located = plan(edits, manuscript, highest_id(parts), ids)
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
        found = _count(len(located), "edit")
        print(f"dry run: {found} found; {args.out} would be written; nothing written")
        return 0
    dates = revision_dates(when, utc=args.utc)
    out = apply(parts, located, args.author, dates)
    changed = {name: text for name, text in out.items() if text != parts[name]}
    with tempfile.TemporaryDirectory(dir=args.tmp) as scratch:
        copy = os.path.join(scratch, "copy.docx")
        docx.write_copy(copy, changed)
        made = Docx(copy)
        written = made.texts()
        results = verify(parts, written, located, args.author, dates)
        stray = docx.strayed(made, changed)
        if stray and results[3][1]:
            results[3] = ("package", False, f"{stray} is not byte-identical in the copy")
        sound = all(passed for _, passed, _ in results)
        for found, passed in zip(located, edit_results(parts, written, located)):
            status = "PASS" if passed else "FAIL"
            print(edit_line(found, found.text, _place(manuscript, found), status))
        for name, passed, detail in results:
            print(f"{name}: {'PASS' if passed else 'FAIL'}: {detail}")
        if sound or args.keep_on_failure:
            _install(copy, args.out)
    if not sound:
        outcome = (
            f"the failed copy was kept at {args.out}"
            if args.keep_on_failure
            else f"{args.out} was not written"
        )
        print(f"propose-edits: verification failed; {outcome}", file=sys.stderr)
        return 1
    print(f"wrote {args.out}")
    return 0

def _ids(edits, manuscript, registry):
    """Where the notes that edits name by permanent ID now are, from the registry
    (`registry.where_now`); None when no edit names one. The registry is only read."""
    by_id = [edit for edit in edits if edit.where[0] == "id"]
    if not by_id:
        return None
    if not registry:
        first = by_id[0]
        raise Refusal(
            f"{first.name} names a note by its permanent ID ({first.where[1]});"
            " give the registry with --registry FILE"
        )
    try:
        with open(registry, encoding="utf-8") as file:
            entries = load_registry(file.read()).entries
    except FileNotFoundError:
        raise Refusal(f"{registry}: no such file") from None
    except RegistryError as error:
        raise Refusal(f"{registry} cannot be used: {error}") from None
    return where_now([edit.where[1] for edit in by_id], read_notes(manuscript), entries)


def _install(copy, out):
    """Put the finished copy at `out` in one step, so that `out` is never seen half
    written: the bytes go to a name beside it, which then takes its place."""
    partial = f"{out}.partial-{os.getpid()}"
    try:
        shutil.copyfile(copy, partial)
        os.replace(partial, out)
    finally:
        if os.path.exists(partial):
            os.remove(partial)


def _count(number, noun):
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _place(manuscript, found):
    """Where an edit is, in the author's terms."""
    target = found.target
    if target.place == "body":
        return f"body, paragraph {target.number}"
    kind, _, number = target.place.partition(":")
    label = manuscript.note_label(kind, int(number))
    if found.edit.where[0] == "id":
        return f"{found.edit.where[1]} {ARROW} {label}"
    return label


def _parser():
    parser = argparse.ArgumentParser(
        prog="propose-edits",
        description="Write a copy of a .docx with a list of edits in it as tracked changes."
        " The manuscript itself is only read.",
    )
    parser.add_argument("edits", metavar="EDITS.json", help="the edits file: a JSON list")
    parser.add_argument("--in", dest="manuscript", required=True, metavar="MANUSCRIPT.docx")
    parser.add_argument("--out", required=True, metavar="NEW.docx", help="the copy to write")
    parser.add_argument(
        "--registry",
        metavar="FILE",
        help="note-map's registry, needed when an edit names a note by its permanent ID"
        " (\"where\": \"N-0042\"); it is only read",
    )
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
    parser.add_argument(
        "--keep-on-failure",
        action="store_true",
        help="keep the copy for inspection even if its verification fails",
    )
    parser.add_argument("--tmp", metavar="DIR", help="where to make the scratch folder")
    parser.add_argument(
        "--timeout",
        type=float,
        metavar="SECONDS",
        help="accepted for uniformity with the other commands; this one runs no outside program",
    )
    return parser
