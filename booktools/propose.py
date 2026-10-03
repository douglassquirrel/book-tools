"""Makes the planned changes in the parts of a document and proves the result."""

from booktools.paragraph import Paragraph
from booktools.revise import revise
from booktools.xmlscan import TAG


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
