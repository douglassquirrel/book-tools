"""One paragraph as its reader sees it: the text of its runs joined, and where each
character sits in the XML."""

import html
import re

from booktools.xmlscan import parse

# One character of text as the XML spells it: an entity or a single character.
UNIT = re.compile(r"&[^;]+;|.", re.S)


# What a child of a run is called when an edit is refused for crossing it.
# Children not listed here or in TRANSPARENT are named by their tag.
IN_RUN = {
    "w:tab": "a tab",
    "w:ptab": "a tab",
    "w:br": "a line break",
    "w:cr": "a line break",
    "w:endnoteReference": "a note marker",
    "w:footnoteReference": "a note marker",
    "w:drawing": "a drawing",
    "w:pict": "a drawing",
    "w:object": "a drawing",
    "mc:AlternateContent": "a drawing",
    "w:commentReference": "a comment marker",
    "w:fldChar": "a field",
    "w:instrText": "a field",
}
# Children of a run that an edit may pass over: they hold no content.
TRANSPARENT = {"w:rPr", "w:lastRenderedPageBreak"}
# Marks that sit between runs. Proofing marks are not listed: Word remakes them.
BETWEEN_RUNS = {
    "w:bookmarkStart": "a bookmark",
    "w:bookmarkEnd": "a bookmark",
    "w:commentRangeStart": "the start or end of a comment's range",
    "w:commentRangeEnd": "the start or end of a comment's range",
    # Text someone has already struck out is not part of the text as it stands.
    "w:del": "an existing tracked deletion",
    "w:moveFrom": "an existing tracked deletion",
}
EXISTING_INSERTION = "an existing tracked insertion"
# Elements that wrap runs. An edit may sit wholly inside one but not cross its edge.
WRAPPERS = {
    "w:hyperlink": "a hyperlink",
    "w:smartTag": "a smart tag",
    "w:customXml": "custom XML",
    "w:sdt": "a content control",
    "w:fldSimple": "a field",
    "w:bdo": "a text-direction override",
    "w:dir": "a text-direction override",
    "w:ins": EXISTING_INSERTION,
    "w:moveTo": EXISTING_INSERTION,
}


class Piece:
    """The text of one <w:t>: which run it is in and where it starts in the paragraph."""

    def __init__(self, run, t, start, units):
        self.run = run
        self.t = t
        self.start = start  # offset of its first character in the paragraph's text
        self.units = units  # each character as the XML spells it


class Paragraph:
    def __init__(self, xml):
        self.xml = xml
        self.pieces = []
        self.barriers = []  # (offset in the text, what stands there)
        self.spans = []  # (start, end, what wraps the text between them)
        self._length = 0
        self._walk(parse(xml))
        self.text = "".join(html.unescape(u) for p in self.pieces for u in p.units)

    def _walk(self, node):
        for child in node.children:
            if child.name == "w:r":
                self._run(child)
            elif child.name in BETWEEN_RUNS:
                self.barriers.append((self._length, BETWEEN_RUNS[child.name]))
            elif child.name in WRAPPERS:
                index = len(self.spans)
                self.spans.append(None)
                start = self._length
                self._walk(child)
                self.spans[index] = (start, self._length, WRAPPERS[child.name])
            elif child.name == "w:sdtContent":
                self._walk(child)

    def _run(self, run):
        for child in run.children:
            if child.name == "w:t":
                units = UNIT.findall(self.xml[child.open_end : child.close_start])
                self.pieces.append(Piece(run, child, self._length, units))
                self._length += len(units)
            elif child.name in IN_RUN:
                self.barriers.append((self._length, IN_RUN[child.name]))
            elif child.name not in TRANSPARENT:
                self.barriers.append((self._length, f"a special character ({child.name})"))

    def find(self, needle):
        """Return (start, end) in the paragraph's text for every place `needle` occurs."""
        found = []
        at = self.text.find(needle) if needle else -1
        while at != -1:
            found.append((at, at + len(needle)))
            at = self.text.find(needle, at + 1)
        return found
