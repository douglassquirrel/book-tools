"""Writes one change into a paragraph's XML as a tracked deletion and insertion."""

import re

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
    first, k1 = _piece_holding(paragraph, change.start)
    last, k2 = _piece_holding(paragraph, change.end - 1)
    k2 += 1
    head, tail = first.run, last.run
    cut_left = k1 > 0
    cut_right = k2 < len(last.units)
    before = xml[head.start : first.t.start]
    after = xml[last.t.end : tail.end]
    if first is last:
        whole = k1 == 0 and k2 == len(first.units)
        text = xml[first.t.start : first.t.end] if whole else _text(first.units[k1:k2])
    else:
        text = (
            (_text(first.units[k1:]) if cut_left else xml[first.t.start : first.t.end])
            + xml[first.t.end : last.t.start]
            + (_text(last.units[:k2]) if cut_right else xml[last.t.start : last.t.end])
        )
    left = before + _text(first.units[:k1]) + "</w:r>" if cut_left else ""
    deleted = (
        (_shell(xml, head) if cut_left else before) + text + ("</w:r>" if cut_right else after)
    )
    right = _shell(xml, tail) + _text(last.units[k2:]) + after if cut_right else ""
    return (
        xml[: head.start]
        + left
        + f'<w:del w:id="{change.del_id}"{stamp}>{_as_deleted(deleted)}</w:del>'
        + f'<w:ins w:id="{change.ins_id}"{stamp}><w:r>{_formatting(xml, head)}'
        + _text([_escape(change.new)])
        + "</w:r></w:ins>"
        + right
        + xml[tail.end :]
    )

def _piece_holding(paragraph, offset):
    """The piece of text holding the character at `offset`, and the offset within it."""
    for piece in paragraph.pieces:
        if piece.start <= offset < piece.start + len(piece.units):
            return piece, offset - piece.start
    raise IndexError(offset)


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
