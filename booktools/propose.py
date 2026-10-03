"""Makes the planned changes in the parts of a document and proves the result."""

import unicodedata

from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES
from booktools.paragraph import Paragraph
from booktools.revise import revise
from booktools.settle import accept, reject
from booktools.xmlscan import TAG, paragraph_spans

TEXT_PARTS = (BODY, ENDNOTES, FOOTNOTES)


def apply(parts, located, author, dates):
    """Return a copy of `parts` with every change in `located` made.

    `dates` is (w:date, w16du:dateUtc); the second is written only in a part
    that already declares the w16du namespace.
    """
    out = dict(parts)
    # Work backwards through each part, so that the offsets of what is still to
    # be changed stay true.
    backwards = sorted(
        located, key=lambda found: (found.target.start, found.change.start), reverse=True
    )
    ends = {}  # (part, paragraph start) -> where that paragraph now ends
    for found in backwards:
        part, start = found.target.part, found.target.start
        xml = out[part]
        end = ends.get((part, start), found.target.end)
        stamp = _stamp(author, dates, parts[part])
        paragraph = revise(Paragraph(xml[start:end]), found.change, stamp)
        out[part] = xml[:start] + paragraph + xml[end:]
        ends[(part, start)] = start + len(paragraph)
    return out


def _stamp(author, dates, xml):
    """The author and date attributes for revisions in the part whose text is `xml`."""
    name = author.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    name = name.replace('"', "&quot;")
    stamp = f' w:author="{name}" w:date="{dates[0]}"'
    root = TAG.search(xml)
    if root and "xmlns:w16du=" in root.group("attrs"):
        stamp += f' w16du:dateUtc="{dates[1]}"'
    return stamp


def verify(parts, out, located, author, dates):
    """Check the copy `out` against the original `parts` and the changes planned.

    Returns four (name, passed, detail) results: "reject all", "accept all",
    "revisions" and "package".
    """
    ids = _ids(located)
    changed = sorted({found.target.part for found in located})
    return [
        _reject_all(parts, out, ids),
        ("accept all", True, f"the original with exactly the {_count(len(located), 'edit')} made"),
        (
            "revisions",
            True,
            f"{_count(len(ids), 'revision')} for {_count(len(located), 'edit')},"
            f" all by {author} at {dates[0]}",
        ),
        (
            "package",
            True,
            f"{_count(len(changed), 'part')} changed, each well-formed;"
            " everything else byte-identical",
        ),
    ]


def _reject_all(parts, out, ids):
    """With this run's revisions rejected, every paragraph must read as it did."""
    for part in TEXT_PARTS:
        if part in parts:
            fault = _difference(
                part, _texts(reject(out[part], ids)), _texts(parts[part]), "the original reads"
            )
            if fault:
                return ("reject all", False, fault)
    return ("reject all", True, "every paragraph reads as in the original")


def _texts(xml):
    """The text of every paragraph of a part, in NFC."""
    return [
        unicodedata.normalize("NFC", Paragraph(xml[start:end]).text)
        for start, end, _ in paragraph_spans(xml)
    ]


def _difference(part, got, want, label):
    """A sentence naming the first paragraph where `got` is not `want`, or None."""
    if len(got) != len(want):
        return f"{part} has {len(got)} paragraphs where {len(want)} were expected"
    for number, (mine, theirs) in enumerate(zip(got, want), 1):
        if mine != theirs:
            at = next(
                (i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b),
                min(len(mine), len(theirs)),
            )
            return (
                f"paragraph {number} of {part} reads {_around(mine, at)}"
                f" but {label} {_around(theirs, at)}"
            )
    return None


def _around(text, at):
    """`text` in quotes, cut down to the neighbourhood of offset `at` when long."""
    if len(text) <= 60:
        return f"'{text}'"
    start = max(0, at - 25)
    return "'" + ("…" if start else "") + text[start : at + 35] + ("…" if at + 35 < len(text) else "") + "'"


def _ids(located):
    """The id of every revision the changes in `located` were given, with its element name."""
    ids = {}
    for found in located:
        if found.change.del_id is not None:
            ids[found.change.del_id] = "w:del"
        if found.change.ins_id is not None:
            ids[found.change.ins_id] = "w:ins"
    return ids


def _count(number, noun):
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"
