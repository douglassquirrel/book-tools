"""compare-saves: what changed between two saves of a manuscript, in words, formatting
and structure."""

import argparse
import subprocess

from booktools import cli
from booktools.compare import compare_part
from booktools.counts import structure_lines
from booktools.docx import Docx
from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES
from booktools.textdiff import PANDOC, text_diff


def main(argv=None):
    """Run the command; return its exit code."""
    return cli.run("compare-saves", _parser(), _run, argv)


def _run(args):
    old_path, new_path = args.saves
    old, new = Docx(old_path), Docx(new_path)
    print(f"old: {old_path}")
    print(f"new: {new_path}")
    if args.no_text_diff:
        print("text diff left out (--no-text-diff)")
    if not args.no_counts:
        print()
        for line in structure_lines(old, new, utc=args.utc):
            print(line)
    print()
    print("== Paragraph by paragraph")
    old_parts, new_parts = old.texts(), new.texts()
    for part in (BODY, ENDNOTES, FOOTNOTES):
        if part in old_parts or part in new_parts:
            was, now = old_parts.get(part, ""), new_parts.get(part, "")
            for line in compare_part(part, was, now, args.ignore_font):
                print(line)
    if not args.no_text_diff:
        print()
        print("== Text diff (body and notes, as pandoc reads them)")
        for line in text_diff(_markdown(old_path), _markdown(new_path)) or ["no differences"]:
            print(line)
    return 0


def _markdown(path):
    """The text of a .docx as pandoc reads it."""
    done = subprocess.run(PANDOC + [path], stdin=subprocess.DEVNULL, capture_output=True)
    return done.stdout.decode("utf-8")


def _parser():
    parser = argparse.ArgumentParser(
        prog="compare-saves",
        description="Say what changed between two saves of a manuscript: structure and"
        " counts, each paragraph's words and formatting, and a text diff of body and notes.",
    )
    parser.add_argument("saves", nargs="+", metavar="FILE", help="OLD.docx NEW.docx")
    parser.add_argument(
        "--ignore-font",
        action="append",
        default=[],
        metavar="NAME",
        help="report a paragraph whose only difference is this font name as FONT-NAME-ONLY"
        " (may be given more than once)",
    )
    parser.add_argument("--no-text-diff", action="store_true", help="leave out the text diff")
    parser.add_argument(
        "--no-counts", action="store_true", help="leave out the structure and counts"
    )
    parser.add_argument(
        "--utc", action="store_true", help="show times in UTC instead of London time"
    )
    parser.add_argument("--tmp", metavar="DIR", help="where to make the scratch folder")
    return parser
