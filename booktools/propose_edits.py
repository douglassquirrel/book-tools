"""propose-edits: write a copy of a .docx with a list of edits in it as tracked changes."""

import argparse
import os
import shutil
import tempfile
from datetime import datetime, timezone

from booktools.clock import revision_dates
from booktools.docx import Docx
from booktools.editsfile import parse_edits
from booktools.manuscript import Manuscript
from booktools.plan import plan
from booktools.propose import apply, highest_id, verify
from booktools.report import edit_line


def main(argv=None, now=None):
    """Run the command; return its exit code. `now` gives the current time (for tests)."""
    args = _parser().parse_args(argv)
    now = now or (lambda: datetime.now(timezone.utc))
    with open(args.edits, encoding="utf-8") as file:
        edits = parse_edits(file.read())
    docx = Docx(args.manuscript)
    parts = docx.texts()
    manuscript = Manuscript(parts)
    located = plan(edits, manuscript, highest_id(parts))
    dates = revision_dates(now())
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
    parser.add_argument("--tmp", metavar="DIR", help="where to make the scratch folder")
    return parser
