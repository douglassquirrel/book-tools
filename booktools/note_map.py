"""note-map: keep a permanent ID for every note, and map each ID to its current number."""

import argparse
import hashlib
import os
import re
import shutil
import sys

from booktools import cli
from booktools.cli import Refusal
from booktools.docx import Docx, DocxError
from booktools.extract import ExtractError, reading_text
from booktools.manuscript import Manuscript
from booktools.notemap import LABEL, map_lines, map_markdown, map_rows, where
from booktools.notes import read_notes
from booktools.pandoc import INSTALL, NoMarkdown, markdown
from booktools.registry import (
    AssignError,
    Registry,
    RegistryError,
    dump_registry,
    load_registry,
    match,
    update,
)

ASSIGN = re.compile(r"(new|[^=\s]+)=(?:(endnote|footnote):)?([1-9][0-9]*)$")


def main(argv=None):
    """Run the command; return its exit code."""
    return cli.run(
        "note-map", _parser(), _run, argv, interrupted="interrupted; nothing written"
    )


def _run(args):
    try:
        docx = Docx(args.manuscript)
    except DocxError as error:
        raise Refusal(str(error)) from None
    with open(args.manuscript, "rb") as file:
        save = hashlib.sha256(file.read()).hexdigest()
    files = ((args.registry, "registry"), (args.map, "map"), (args.extract, "reading text"))
    for path, what in files:
        if path is None:
            continue
        if os.path.realpath(path) == os.path.realpath(args.manuscript):
            raise Refusal(f"{path} is the manuscript itself; give the {what} another name")
        folder = os.path.dirname(path) or "."
        if not os.path.isdir(folder):
            raise Refusal(f"the folder {folder} does not exist")
    if args.extract:
        others = [os.path.realpath(path) for path in (args.registry, args.map) if path]
        if os.path.realpath(args.extract) in others:
            raise Refusal(f"{args.extract} is given twice; give the reading text another name")
        if os.path.exists(args.extract) and not args.force:
            raise Refusal(f"{args.extract} already exists; give another name or add --force")
        if shutil.which("pandoc") is None:
            raise Refusal(f"pandoc was not found; --extract needs it. {INSTALL}")
    registry, before = Registry(), None
    if os.path.exists(args.registry):
        with open(args.registry, encoding="utf-8") as file:
            before = file.read()
        try:
            registry = load_registry(before)
        except RegistryError as error:
            raise Refusal(f"{args.registry} cannot be used: {error}") from None
    manuscript = Manuscript(docx.texts())
    notes = read_notes(manuscript)
    assign, flags = _assignments(args.assign, notes)
    try:
        matching = match(notes, registry.live(), assign)
    except AssignError as error:
        flag = next((f for key, f in flags.items() if key in str(error)), args.assign[0])
        raise Refusal(f"--assign {flag}: {error}") from None
    if matching.unclear:
        for note, candidates in matching.unclear:
            print(
                f'unclear: {note.place} "{_short(note.text)}" in the sentence "{note.sentence}"'
            )
            for entry in candidates:
                assignment = f"--assign {entry.id}={note.place}"
                print(f'  if it is {entry.id} "{_short(entry.text)}": {assignment}')
            print(f"  if it is a new note: --assign new={note.place}")
        count = len(matching.unclear)
        which = "1 note is" if count == 1 else f"{count} notes are"
        print(
            f"note-map: {which} unclear and was not guessed; nothing written."
            " Run again with --assign for each",
            file=sys.stderr,
        )
        return 1
    updated, ids = update(registry, matching, save)
    count = "1 note" if len(notes) == 1 else f"{len(notes)} notes"
    summary = (
        f"{count}: {len(matching.carried)} carried, {len(matching.new)} new,"
        f" {len(matching.retired)} retired"
    )
    print(f"dry run: {summary}; nothing written" if args.dry_run else summary)
    for note in matching.new:
        print(f"new: {ids[note.place]} {note.place} {_short(note.text)}")
    for entry in matching.retired:
        print(f"retired: {entry.id} {_short(entry.text)}")
    retired = [entry.id for entry in updated.entries if entry.retired_in is not None]
    rows = map_rows(notes, ids, updated)
    if not args.map:
        for line in map_lines(rows, retired):
            print(line)
    if args.dry_run:
        if args.extract:
            print(f"dry run: the reading text {args.extract} would be written")
        return 0
    name = os.path.basename(args.manuscript)
    reading = None
    if args.extract:
        shown = {place: where(number, heading) for _, _, place, number, heading in rows}
        order = [(ids[place], shown[place]) for place in manuscript.note_order()]
        try:
            reading = reading_text(markdown(args.manuscript, args.timeout), order, name, save)
        except (NoMarkdown, ExtractError) as error:
            print(
                f"note-map: no reading text: {error}; nothing written. To bring the registry"
                " up to date without it, run again without --extract",
                file=sys.stderr,
            )
            return 1
    if args.map:
        _write(args.map, map_markdown(rows, retired, name, save))
    after = dump_registry(updated)
    if after != before:
        _write(args.registry, after)
    if reading is not None:
        _write(args.extract, reading)
        print(f"wrote the reading text {args.extract}")
    return 0


def _assignments(given, notes):
    """({note place: ID or "new"}, {place or ID: the flag as typed}) from --assign flags."""
    kinds = sorted({note.kind for note in notes})
    assign, flags = {}, {}
    for flag in given:
        found = ASSIGN.match(flag)
        if not found:
            raise Refusal(
                f"--assign {flag}: must be ID=NUMBER or new=NUMBER,"
                " NUMBER being endnote:N or footnote:N"
            )
        id, kind, number = found.groups()
        if kind is None and len(kinds) > 1:
            raise Refusal(
                f"--assign {flag}: say endnote:{number} or footnote:{number},"
                " since this document has both"
            )
        place = f"{kind or (kinds[0] if kinds else 'endnote')}:{number}"
        assign[place] = id
        flags[place] = flags[id] = flag
    return assign, flags


def _short(text):
    return " ".join(text.split("\n"))[:LABEL]


def _write(path, text):
    """Write a file whole, through a file beside it that then takes its name."""
    partial = f"{path}.partial-{os.getpid()}"
    try:
        with open(partial, "w", encoding="utf-8") as file:
            file.write(text)
        os.replace(partial, path)
    finally:
        if os.path.exists(partial):
            cli.remove("note-map", partial, "the part-written file")


def _parser():
    parser = argparse.ArgumentParser(
        prog="note-map",
        description="Keep a permanent ID for every note of a manuscript across saves, and"
        " write the map from each ID to the note's current number. The manuscript is only"
        " read.",
    )
    parser.add_argument("manuscript", metavar="MANUSCRIPT.docx")
    parser.add_argument(
        "--registry", required=True, metavar="FILE", help="the registry of note IDs (JSON)"
    )
    parser.add_argument(
        "--map", metavar="FILE", help="write the map here as a Markdown table, not to the screen"
    )
    parser.add_argument(
        "--extract",
        metavar="FILE",
        help="also write the reading text here: the manuscript as pandoc reads it (markdown),"
        " with each note's permanent ID in place of its number; needs pandoc",
    )
    parser.add_argument(
        "--force", action="store_true", help="write the reading text even if the file exists"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would change and write nothing"
    )
    parser.add_argument(
        "--assign",
        action="append",
        default=[],
        metavar="ID=NUMBER",
        help="settle an unclear note: this ID is the note now numbered NUMBER (endnote:N or"
        " footnote:N, counted through the document); new=NUMBER says it is a new note",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120,
        metavar="SECONDS",
        help="how long pandoc may take to read the manuscript for --extract (default 120)",
    )
    return parser
