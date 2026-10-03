"""Makes the planned changes in the parts of a document and proves the result."""

import re
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
        _accept_all(parts, out, located, ids),
        _revisions(parts, out, located, ids, author, dates),
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


def _accept_all(parts, out, located, ids):
    """With this run's revisions accepted, the text must be the original with each
    edit made as a plain replacement, and nothing else."""
    for part in TEXT_PARTS:
        if part not in parts:
            continue
        wanted = []
        for number, (start, end, _) in enumerate(paragraph_spans(parts[part]), 1):
            text = Paragraph(parts[part][start:end]).text
            here = [f for f in located if (f.target.part, f.target.number) == (part, number)]
            for found in sorted(here, key=lambda f: f.start, reverse=True):
                text = text[: found.start] + found.edit.replace + text[found.end :]
            wanted.append(unicodedata.normalize("NFC", text))
        fault = _difference(part, _texts(accept(out[part], ids)), wanted, "the edits ask for")
        if fault:
            return ("accept all", False, fault)
    made = _count(len(located), "edit")
    return ("accept all", True, f"the original with exactly the {made} made")


def _revisions(parts, out, located, ids, author, dates):
    """Each edit must have exactly its own revisions, stamped with this run's author
    and date, and the copy must hold no other new tracked change."""
    seen = {}  # id -> [(part, attributes as written)] for elements of the expected name
    before = after = 0
    for part in TEXT_PARTS:
        if part not in parts:
            continue
        before += len(_tracked(parts[part]))
        for name, attrs in _tracked(out[part]):
            after += 1
            found = re.search(r'\bw:id="(-?\d+)"', attrs)
            id = int(found.group(1)) if found else None
            if ids.get(id) == name:
                seen.setdefault(id, []).append((part, attrs))
    for id in sorted(ids):
        if id not in seen:
            return ("revisions", False, f"revision {id} ({ids[id]}) is missing from the copy")
        if len(seen[id]) > 1:
            return ("revisions", False, f"revision {id} appears {len(seen[id])} times in the copy")
        part, attrs = seen[id][0]
        if attrs != f' w:id="{id}"' + _stamp(author, dates, parts[part]):
            fault = f"revision {id} in {part} does not carry the author and date of this run"
            return ("revisions", False, fault)
    if after - before != len(ids):
        return (
            "revisions",
            False,
            f"the copy holds {after - before} tracked changes more than the original;"
            f" the edits account for {len(ids)}",
        )
    return (
        "revisions",
        True,
        f"{_count(len(ids), 'revision')} for {_count(len(located), 'edit')},"
        f" all by {author} at {dates[0]}",
    )


def _tracked(xml):
    """(name, attributes) of every tracked insertion, deletion or move that wraps content."""
    names = ("w:ins", "w:del", "w:moveFrom", "w:moveTo")
    return [
        (tag.group("name"), tag.group("attrs"))
        for tag in TAG.finditer(xml)
        if tag.group("name") in names and not tag.group("close") and not tag.group("empty")
    ]


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
