"""compare-saves: what changed between two saves of a manuscript, in words, formatting
and structure."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import timezone

from booktools import cli
from booktools.cli import Refusal
from booktools.clock import instant, london
from booktools.compare import compare_part
from booktools.counts import structure_lines
from booktools.docx import Docx, DocxError
from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES
from booktools.textdiff import PANDOC, text_diff


def main(argv=None):
    """Run the command; return its exit code."""
    return cli.run("compare-saves", _parser(), _run, argv)


def _run(args):
    count = len(args.saves)
    if args.git and count not in (2, 3):
        raise Refusal("with --git give OLDREV [NEWREV] FILE.docx")
    if not args.git and count != 2:
        raise Refusal("give two saves, OLD.docx NEW.docx (or --git OLDREV [NEWREV] FILE.docx)")
    if not args.no_text_diff and shutil.which("pandoc") is None:
        raise Refusal(
            "pandoc was not found; the text diff needs it. Install it with"
            " `brew install pandoc`, or on a Mac without Homebrew with the installer package"
            " from pandoc.org; or leave the text diff out with --no-text-diff"
        )
    if args.git and shutil.which("git") is None:
        raise Refusal("git was not found; --git needs it")
    with tempfile.TemporaryDirectory(dir=args.tmp) as scratch:
        try:
            return _report(args, scratch)
        except Failed as failure:
            print(f"compare-saves: {failure}", file=sys.stderr)
            return 1


class Failed(Exception):
    """The run happened and could not be completed: exit 1."""


def _report(args, scratch):
    if args.git:
        *revisions, file = args.saves
        sides = [_committed(file, revision, scratch, args) for revision in revisions]
        if len(sides) == 1:
            sides.append((file, f"{file} as it is on disk"))
        (old_path, old_name), (new_path, new_name) = sides
    else:
        old_path, new_path = old_name, new_name = args.saves
    try:
        old, new = Docx(old_path), Docx(new_path)
    except DocxError as error:
        raise Failed(str(error)) from None
    print(f"old: {old_name}")
    print(f"new: {new_name}")
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
            raise Failed(f"no text diff: {error}") from None
        for line in words or ["no differences"]:
            print(line)
    return 0


def _committed(file, revision, scratch, args):
    """Fetch `file` as committed at `revision` into the scratch folder.
    Returns (the path of the copy, how to name that side in the report)."""
    folder, name = os.path.split(os.path.abspath(file))
    shown = _git(["git", "-C", folder, "show", f"{revision}:./{name}"], args.timeout)
    if shown.returncode != 0:
        said = shown.stderr.decode("utf-8", "replace").strip().splitlines()
        if said and "not a git repository" in said[0]:
            raise Refusal(f"{file} is not in a git repository")
        raise Refusal(
            f"{revision} does not hold {name} (git said: {said[0] if said else 'nothing'})"
        )
    copy = os.path.join(scratch, f"{len(os.listdir(scratch))}-{name}")
    with open(copy, "wb") as out:
        out.write(shown.stdout)
    logged = _git(["git", "-C", folder, "log", "-1", "--format=%H %cI", revision], args.timeout)
    commit, _, date = logged.stdout.decode("utf-8", "replace").strip().partition(" ")
    try:
        moment = instant(date).astimezone(timezone.utc)
        when = (moment if args.utc else london(moment)).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        when = date
    return copy, f"{file} at {revision} (commit {commit[:7]}, {when})"


def _git(command, timeout):
    """Run one read-only git command; the kit never changes a repository."""
    try:
        return subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise Failed(f"git did not answer within {timeout:g} seconds") from None


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
