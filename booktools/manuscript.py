"""The text of a manuscript that an edit can name: body paragraphs and notes."""

import re

from booktools.xmlscan import TAG, paragraph_spans

BODY = "word/document.xml"
ENDNOTES = "word/endnotes.xml"
FOOTNOTES = "word/footnotes.xml"


class Target:
    """One paragraph an edit may be made in."""

    def __init__(self, part, number, start, end, place):
        self.part = part  # the name of the part it is in
        self.number = number  # its position among the part's paragraphs, from 1
        self.start = start  # offsets in the part's XML
        self.end = end
        self.place = place  # "body", "endnote:42" or "footnote:3"
        self.note = int(place.partition(":")[2] or 0)  # 42, 3; 0 for the body


class Manuscript:
    def __init__(self, parts):
        """`parts` maps part names to their XML text; the body is required."""
        self.parts = parts
        self.body = []  # Targets
        self.endnotes = []  # one list of Targets per endnote, in document order
        self.footnotes = []
        for number, (start, end, depth) in enumerate(paragraph_spans(parts[BODY]), 1):
            if depth == 1:
                self.body.append(Target(BODY, number, start, end, "body"))
        self.endnotes = self._notes("endnote", ENDNOTES)
        self.footnotes = self._notes("footnote", FOOTNOTES)

    def _notes(self, kind, part):
        """The paragraphs of each note of one kind, in the order of the markers in the body."""
        xml = self.parts.get(part)
        if xml is None:
            return []
        spans = {}  # the note's id -> (start, end) of its element
        for tag in TAG.finditer(xml):
            if tag.group("name") != "w:" + kind:
                continue
            if tag.group("close"):
                spans[opened] = (spans[opened], tag.end())
            elif not tag.group("empty"):
                opened = _id(tag.group("attrs"))
                spans[opened] = tag.start()
        paragraphs = list(enumerate(paragraph_spans(xml), 1))
        notes = []
        marker = re.compile(rf"<w:{kind}Reference\b([^>]*)>")
        for found in marker.finditer(self.parts[BODY]):
            if _id(found.group(1)) not in spans:
                continue
            first, last = spans[_id(found.group(1))]
            place = f"{kind}:{len(notes) + 1}"
            notes.append(
                [
                    Target(part, number, start, end, place)
                    for number, (start, end, depth) in paragraphs
                    if depth == 1 and first <= start and end <= last
                ]
            )
        return notes


def _id(attrs):
    found = re.search(r'\bw:id="(-?\d+)"', attrs)
    return found.group(1) if found else None
