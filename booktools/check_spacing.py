"""check-spacing: the paragraphs of a manuscript that are not at the expected line spacing."""

import argparse

from booktools import cli
from booktools.docx import Docx
from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES, STYLES
from booktools.spacing import Styles, measure, report

PARTS = ((BODY, "TEXT"), (ENDNOTES, "NOTES"), (FOOTNOTES, "FOOTNOTES"))


def main(argv=None):
    """Run the command; return its exit code."""
    return cli.run("check-spacing", _parser(), _run, argv)


def _run(args):
    parts = Docx(args.manuscript).texts()
    styles = Styles(parts[STYLES])
    for part, label in PARTS:
        if part in parts:
            rows = measure(parts[part], styles, in_body=part == BODY)
            for line in report(label, rows, "double", args.verbose):
                print(line)
    return 1


def _parser():
    parser = argparse.ArgumentParser(
        prog="check-spacing",
        description="List the paragraphs of a manuscript, in the text and in the notes,"
        " that are not at the expected line spacing, following Word's style inheritance.",
    )
    parser.add_argument("manuscript", metavar="MANUSCRIPT.docx")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="list each paragraph that does not match"
    )
    return parser
