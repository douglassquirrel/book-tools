"""Writes one change into a paragraph's XML as a tracked deletion and insertion."""

import re

from booktools.paragraph import TRANSPARENT

WHITESPACE = tuple(" \t\n\r")


class Change:
    """The text from `start` to `end` of a paragraph is to become `new`.

    `start == end` is a pure insertion; it goes after the character before
    `start` when `after` is true and before the character at `start` otherwise.
    An empty `new` is a pure deletion. `del_id` and `ins_id` are the revision
    ids to use.
    """

    def __init__(self, start, end, new, del_id=None, ins_id=None, after=True):
        self.start = start
        self.end = end
        self.new = new
        self.del_id = del_id
        self.ins_id = ins_id
        self.after = after


def revise(paragraph, change, stamp):
    """Return the paragraph's XML with `change` made as a tracked change.

    `stamp` is the author and date attributes every revision carries.
    """
    xml = paragraph.xml
    if change.start == change.end:
        return _insert(paragraph, change, stamp)
    first, k1 = _piece_holding(paragraph, change.start)
    last, k2 = _piece_holding(paragraph, change.end - 1)
    k2 += 1
    head, tail = first.run, last.run
    from_start = k1 == 0
    to_end = k2 == len(last.units)
    cut_left = not from_start or _content_before(head, first.t)
    cut_right = not to_end or _content_after(tail, last.t)
    before = xml[head.start : first.t.start]
    after = xml[last.t.end : tail.end]
    if first is last:
        whole = from_start and to_end
        text = xml[first.t.start : first.t.end] if whole else _text(first.units[k1:k2])
    else:
        text = (
            (xml[first.t.start : first.t.end] if from_start else _text(first.units[k1:]))
            + xml[first.t.end : last.t.start]
            + (xml[last.t.start : last.t.end] if to_end else _text(last.units[:k2]))
        )
    left = ""
    if cut_left:
        left = before + ("" if from_start else _text(first.units[:k1])) + "</w:r>"
    deleted = (
        (_shell(xml, head) if cut_left else before) + text + ("</w:r>" if cut_right else after)
    )
    right = ""
    if cut_right:
        right = _shell(xml, tail) + ("" if to_end else _text(last.units[k2:])) + after
    return (
        xml[: head.start]
        + left
        + f'<w:del w:id="{change.del_id}"{stamp}>{_as_deleted(deleted)}</w:del>'
        + _inserted(xml, head, change, stamp)
        + right
        + xml[tail.end :]
    )

def _insert(paragraph, change, stamp):
    """A pure insertion: nothing is deleted, and at most one run is cut in two."""
    xml = paragraph.xml
    if change.after:
        piece, k = _piece_holding(paragraph, change.start - 1)
        k += 1
    else:
        piece, k = _piece_holding(paragraph, change.start)
    run = piece.run
    inserted = _inserted(xml, run, change, stamp)
    at_start = k == 0
    at_end = k == len(piece.units)
    if at_start and not _content_before(run, piece.t):
        return xml[: run.start] + inserted + xml[run.start :]
    if at_end and not _content_after(run, piece.t):
        return xml[: run.end] + inserted + xml[run.end :]
    whole = xml[piece.t.start : piece.t.end]
    left = "" if at_start else whole if at_end else _text(piece.units[:k])
    right = "" if at_end else whole if at_start else _text(piece.units[k:])
    return (
        xml[: piece.t.start]
        + left
        + "</w:r>"
        + inserted
        + _shell(xml, run)
        + right
        + xml[piece.t.end :]
    )


def _content_before(run, t):
    """Whether the run holds anything but formatting before its text element `t`."""
    return any(c.name not in TRANSPARENT for c in run.children if c.start < t.start)


def _content_after(run, t):
    """Whether the run holds anything that matters after its text element `t`."""
    return any(c.name not in TRANSPARENT for c in run.children if c.start > t.start)

def _inserted(xml, run, change, stamp):
    """The new text as a tracked insertion formatted as `run` is, or nothing."""
    if not change.new:
        return ""
    return (
        f'<w:ins w:id="{change.ins_id}"{stamp}><w:r>{_formatting(xml, run)}'
        + _text([_escape(change.new)])
        + "</w:r></w:ins>"
    )


def _piece_holding(paragraph, offset):
    """The piece of text holding the character at `offset`, and the offset within it."""
    piece = next(p for p in paragraph.pieces if p.start <= offset < p.start + len(p.units))
    return piece, offset - piece.start


def _formatting(xml, run):
    """The run's <w:rPr>, exactly as written, or nothing."""
    for child in run.children:
        if child.name == "w:rPr":
            return xml[child.start : child.end]
    return ""


def _shell(xml, run):
    """The start of a run that is formatted as `run` is: its start tag and formatting."""
    return xml[run.start : run.open_end] + _formatting(xml, run)


def _text(units):
    """A <w:t> holding `units`, each a character as XML spells it."""
    text = "".join(units)
    keep = ' xml:space="preserve"' if text[:1] in WHITESPACE or text[-1:] in WHITESPACE else ""
    return f"<w:t{keep}>{text}</w:t>"


def _as_deleted(runs):
    """The same runs with their text marked as deleted text."""
    return re.sub(r"<(/?)w:t(?=[\s>/])", r"<\1w:delText", runs)


def _escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
