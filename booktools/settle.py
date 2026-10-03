"""Reads a part as it would stand with a chosen set of tracked changes accepted or
rejected. Used to prove that a copy holds the listed edits and nothing else."""

import re

from booktools.xmlscan import TAG

ID = re.compile(r'\bw:id="(-?\d+)"')
DELETED_TEXT = re.compile(r"<(/?)w:delText(?=[\s>/])")


def accept(xml, ids):
    """Return `xml` with the revisions whose ids are in `ids` accepted."""
    return _settle(xml, ids, keep="w:ins")


def reject(xml, ids):
    """Return `xml` with the revisions whose ids are in `ids` rejected."""
    return _settle(xml, ids, keep="w:del")


def _settle(xml, ids, keep):
    """Unwrap the chosen revisions named `keep`; remove the other kind with its content."""
    out = []
    done = 0
    opened = []
    for tag in TAG.finditer(xml):
        if tag.group("name") not in ("w:ins", "w:del") or tag.group("empty"):
            continue
        if not tag.group("close"):
            opened.append(tag)
            continue
        start = opened.pop()
        found = ID.search(start.group("attrs"))
        if not found or int(found.group(1)) not in ids:
            continue
        out.append(xml[done : start.start()])
        if tag.group("name") == keep:
            inner = xml[start.end() : tag.start()]
            out.append(DELETED_TEXT.sub(r"<\1w:t", inner))
        done = tag.end()
    out.append(xml[done:])
    return "".join(out)
