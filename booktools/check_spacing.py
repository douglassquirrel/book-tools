"""check-spacing: the paragraphs of a manuscript that are not at the expected line spacing."""

import argparse

from booktools import cli
from booktools.cli import Refusal
from booktools.docx import Docx, DocxError
from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES, STYLES
from booktools.spacing import Styles, measure, report

NO_STYLES = (
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
)
PARTS = ((BODY, "TEXT"), (ENDNOTES, "NOTES"), (FOOTNOTES, "FOOTNOTES"))


def main(argv=None):
    """Run the command; return its exit code."""
    return cli.run("check-spacing", _parser(), _run, argv)


def _run(args):
    expect, wanted = _expectation(args.expect)
    try:
        parts = Docx(args.manuscript).texts()
    except DocxError as error:
        raise Refusal(str(error)) from None
    styles = Styles(parts.get(STYLES, NO_STYLES))
    all_match = True
    for part, label in PARTS:
        if part in parts:
            rows = measure(parts[part], styles, expect, in_body=part == BODY)
            all_match = all_match and all(row[4] for row in rows)
            for line in report(label, rows, wanted, args.verbose):
                print(line)
    return 0 if all_match else 1


def _expectation(text):
    """(the expected line value in 240ths, the word for it) for what --expect was given."""
    named = {"double": 480, "single": 240}
    if text in named:
        return named[text], text
    if text.isdigit() and int(text) > 0:
        return int(text), f"at {int(text) / 240:g} lines"
    raise Refusal(
        "--expect must be double, single, or a whole number of 240ths of a line"
        " (360 is one and a half)"
    )


def _parser():
    parser = argparse.ArgumentParser(
        prog="check-spacing",
        description="List the paragraphs of a manuscript, in the text and in the notes,"
        " that are not at the expected line spacing, following Word's style inheritance.",
    )
    parser.add_argument("manuscript", metavar="MANUSCRIPT.docx")
    parser.add_argument(
        "--expect",
        default="double",
        metavar="double|single|N",
        help="the spacing every paragraph should have: double (the default), single, or N"
        " 240ths of a line",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="list each paragraph that does not match"
    )
    return parser
