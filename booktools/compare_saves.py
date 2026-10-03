"""compare-saves: what changed between two saves of a manuscript, in words, formatting
and structure."""

import argparse
import shutil
import subprocess
import sys

from booktools import cli
from booktools.cli import Refusal
from booktools.compare import compare_part
from booktools.counts import structure_lines
from booktools.docx import Docx, DocxError
from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES
from booktools.textdiff import PANDOC, text_diff


def main(argv=None):
    """Run the command; return its exit code."""
    return cli.run("compare-saves", _parser(), _run, argv)


def _run(args):
    if len(args.saves) != 2:
        raise Refusal("give two saves, OLD.docx NEW.docx (or --git OLDREV [NEWREV] FILE.docx)")
    if not args.no_text_diff and shutil.which("pandoc") is None:
        raise Refusal(
            "pandoc was not found; the text diff needs it. Install it with"
            " `brew install pandoc`, or on a Mac without Homebrew with the installer package"
            " from pandoc.org; or leave the text diff out with --no-text-diff"
        )
    old_path, new_path = args.saves
    try:
        old, new = Docx(old_path), Docx(new_path)
    except DocxError as error:
        print(f"compare-saves: {error}", file=sys.stderr)
        return 1
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
        try:
            words = text_diff(
                _markdown(old_path, args.timeout), _markdown(new_path, args.timeout)
            )
        except NoMarkdown as error:
            print(f"compare-saves: no text diff: {error}", file=sys.stderr)
            return 1
        for line in words or ["no differences"]:
            print(line)
    return 0


class NoMarkdown(Exception):
    """pandoc could not give the text of a save."""


def _markdown(path, timeout):
    """The text of a .docx as pandoc reads it."""
    try:
        done = subprocess.run(
            PANDOC + [path], stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise NoMarkdown(
            f"pandoc did not finish with {path} within {timeout:g} seconds"
        ) from None
    if done.returncode != 0:
        said = done.stderr.decode("utf-8", "replace").strip().splitlines()
        raise NoMarkdown(f"pandoc failed on {path}: {said[0] if said else done.returncode}")
    if not done.stdout:
        raise NoMarkdown(f"pandoc printed nothing for {path}")
    try:
        return done.stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise NoMarkdown(f"pandoc did not print text for {path}") from None


def _parser():
    parser = argparse.ArgumentParser(
        prog="compare-saves",
        description="Say what changed between two saves of a manuscript: structure and"
        " counts, each paragraph's words and formatting, and a text diff of body and notes.",
    )
    parser.add_argument(
        "saves",
        nargs="+",
        metavar="FILE",
        help="OLD.docx NEW.docx; or, with --git, OLDREV [NEWREV] FILE.docx",
    )
    parser.add_argument(
        "--git",
        action="store_true",
        help="compare committed versions of one file: the old side is FILE.docx at OLDREV,"
        " the new side the same file at NEWREV, or as it is on disk",
    )
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
    parser.add_argument(
        "--timeout",
        type=float,
        default=120,
        metavar="SECONDS",
        help="how long pandoc or git may take over one call (default 120)",
    )
    return parser
