"""Makes the planned changes in the parts of a document and proves the result."""

import re
import unicodedata
from xml.etree import ElementTree

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
    return [
        _reject_all(parts, out, ids),
        _accept_all(parts, out, located, ids),
        _revisions(parts, out, located, ids, author, dates),
        _package(parts, out, located),
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


def _package(parts, out, located):
    """Nothing but the edited paragraphs may differ by a single byte, and each
    edited part must still be well-formed XML."""
    edited = {(found.target.part, found.target.number) for found in located}
    changed = sorted({part for part, _ in edited})
    for part in parts:
        fault = None
        if part in changed:
            try:
                ElementTree.fromstring(out[part].encode("utf-8"))
                fault = _strayed(part, parts[part], out[part], edited)
            except ElementTree.ParseError as error:
                fault = f"{part} is not well-formed XML: {error}"
        elif out.get(part) != parts[part]:
            fault = f"{part} has changed and no edit is in it"
        if fault:
            return ("package", False, fault)
    detail = f"{_count(len(changed), 'part')} changed, each well-formed"
    return ("package", True, detail + "; everything else byte-identical")


def _strayed(part, old, new, edited):
    """A sentence naming the first byte-level change outside the edited paragraphs."""

    def outer(xml):
        spans = enumerate(paragraph_spans(xml), 1)
        return [(number, start, end) for number, (start, end, depth) in spans if depth == 1]

    was, now = outer(old), outer(new)
    outside = f"{part} has changed outside its paragraphs"
    if len(was) != len(now):
        return outside
    old_at = new_at = 0
    for (number, old_start, old_end), (_, new_start, new_end) in zip(was, now):
        if old[old_at:old_start] != new[new_at:new_start]:
            return outside
        if (part, number) not in edited and old[old_start:old_end] != new[new_start:new_end]:
            return f"paragraph {number} of {part} was not edited but its XML has changed"
        old_at, new_at = old_end, new_end
    return outside if old[old_at:] != new[new_at:] else None


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
    lead = "…" if start else ""
    trail = "…" if at + 35 < len(text) else ""
    return f"'{lead}{text[start : at + 35]}{trail}'"


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


def highest_id(parts):
    """The highest w:id in any of `parts`; new revisions are numbered above it."""
    found = [int(n) for xml in parts.values() for n in re.findall(r'\bw:id="(\d+)"', xml)]
    return max(found, default=0)


def edit_results(parts, out, located):
    """For each change in `located`, whether its own paragraph in the copy `out` reads
    as the original when rejected and as the edits ask when accepted."""
    ids = _ids(located)
    results = []
    for found in located:
        part, number = found.target.part, found.target.number
        spans = paragraph_spans(out[part])
        if number > len(spans):
            results.append(False)
            continue
        start, end, _ = spans[number - 1]
        paragraph = out[part][start:end]
        wanted = found.text
        here = [f for f in located if (f.target.part, f.target.number) == (part, number)]
        for other in sorted(here, key=lambda f: f.start, reverse=True):
            wanted = wanted[: other.start] + other.edit.replace + wanted[other.end :]
        nfc = unicodedata.normalize
        results.append(
            nfc("NFC", Paragraph(reject(paragraph, ids)).text) == nfc("NFC", found.text)
            and nfc("NFC", Paragraph(accept(paragraph, ids)).text) == nfc("NFC", wanted)
        )
    return results
