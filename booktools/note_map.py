"""note-map: keep a permanent ID for every note, and map each ID to its current number."""

import argparse
import hashlib
import os

from booktools import cli
from booktools.cli import Refusal
from booktools.docx import Docx, DocxError
from booktools.manuscript import Manuscript
from booktools.notemap import LABEL, map_lines, map_rows
from booktools.notes import read_notes
from booktools.registry import Registry, dump_registry, match, update


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
    registry = Registry()
    notes = read_notes(Manuscript(docx.texts()))
    matching = match(notes, registry.live())
    updated, ids = update(registry, matching, save)
    count = "1 note" if len(notes) == 1 else f"{len(notes)} notes"
    print(
        f"{count}: {len(matching.carried)} carried, {len(matching.new)} new,"
        f" {len(matching.retired)} retired"
    )
    for note in matching.new:
        print(f"new: {ids[note.place]} {note.place} {_short(note.text)}")
    retired = [entry.id for entry in updated.entries if entry.retired_in is not None]
    for line in map_lines(map_rows(notes, ids, updated), retired):
        print(line)
    _write(args.registry, dump_registry(updated))
    return 0


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
            os.remove(partial)


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
    return parser
