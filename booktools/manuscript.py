"""The text of a manuscript that an edit can name: body paragraphs and notes."""

import re

from booktools.paragraph import Paragraph
from booktools.sentences import sentence_at
from booktools.xmlscan import TAG, paragraph_spans

BODY = "word/document.xml"
ENDNOTES = "word/endnotes.xml"
FOOTNOTES = "word/footnotes.xml"
SETTINGS = "word/settings.xml"
STYLES = "word/styles.xml"
# A style's id and its name, which says "heading 2" whatever the id is.
STYLE = re.compile(r'<w:style\b[^>]*\bw:styleId="([^"]*)"[^>]*>\s*<w:name w:val="([^"]*)"/>')


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
        self._markers = {"endnote": [], "footnote": []}  # (offset in the body, id), per note
        self._outline = None
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
        opened = None  # (the id, the start) of the note element now open
        for tag in TAG.finditer(xml):
            if tag.group("name") != "w:" + kind:
                continue
            if tag.group("close"):
                if opened is not None:
                    spans[opened[0]] = (opened[1], tag.end())
                opened = None
            elif not tag.group("empty"):
                opened = (_id(tag.group("attrs")), tag.start())
        paragraphs = list(enumerate(paragraph_spans(xml), 1))
        notes = []
        marker = re.compile(rf"<w:{kind}Reference\b([^>]*)>")
        for found in marker.finditer(self.parts[BODY]):
            if _id(found.group(1)) not in spans:
                continue
            first, last = spans[_id(found.group(1))]
            place = f"{kind}:{len(notes) + 1}"
            self._markers[kind].append((found.start(), _id(found.group(1))))
            notes.append(
                [
                    Target(part, number, start, end, place)
                    for number, (start, end, depth) in paragraphs
                    if depth == 1 and first <= start and end <= last
                ]
            )
        return notes

    def note_label(self, kind, number):
        """How the book shows the note counted `number`: under its heading, with the
        number it prints as, then the count, as "Chapter 3, note 7 (endnote:42)"."""
        count = f"{kind}:{number}"
        heading, shown = self.note_place(kind, number)
        if shown is None:
            return count  # the printed number depends on the page it falls on
        return f"{heading}, note {shown} ({count})" if heading else f"note {shown} ({count})"

    def note_place(self, kind, number):
        """(heading, number as printed) for the note counted `number`: the heading is ""
        when there is none above it, the number None when it restarts on every page."""
        restart = self._restart(kind)
        outline = self._outlined()
        markers = [self._paragraph_at(offset) for offset, _ in self._markers[kind]]
        here = markers[number - 1]
        level = None
        shown = number
        if restart == "eachSect":
            section = outline[here][0]
            shown = sum(1 for m in markers[:number] if outline[m][0] == section)
            level = self._chapter_level()
        title = ""
        for _, heading_level, text in reversed(outline[: here + 1]):
            if heading_level and (level is None or heading_level == level):
                title = text
                break
        return title, None if restart == "eachPage" else shown

    def marker_sentence(self, kind, number):
        """The sentence in the body that the marker of the note counted `number` sits in."""
        offset, id = self._markers[kind][number - 1]
        target = self.body[self._paragraph_at(offset)]
        paragraph = Paragraph(self.parts[BODY][target.start : target.end])
        for at, marker_kind, marker_id in paragraph.markers:
            if (marker_kind, marker_id) == (kind, id):
                return sentence_at(paragraph.text, at)
        return ""  # the marker is inside a text box, whose text is not read

    def _restart(self, kind):
        """Where this kind of note starts again from 1: continuous, eachSect or eachPage."""
        block = re.compile(rf"<w:{kind}Pr>.*?</w:{kind}Pr>", re.S)
        for xml in (self.parts.get(SETTINGS, ""), self.parts[BODY]):
            for found in block.finditer(xml):
                setting = re.search(r'<w:numRestart w:val="(\w+)"/>', found.group(0))
                if setting and setting.group(1) != "continuous":
                    return setting.group(1)
        return "continuous"

    def _outlined(self):
        """For each body paragraph: (its section, its heading level or None, its text)."""
        if self._outline is None:
            names = dict(STYLE.findall(self.parts.get(STYLES, "")))
            xml = self.parts[BODY]
            self._outline = []
            section = 0
            for target in self.body:
                paragraph = xml[target.start : target.end]
                style = re.search(r'<w:pStyle w:val="([^"]*)"/>', paragraph)
                level = None
                if style:
                    name = names.get(style.group(1), style.group(1))
                    found = re.match(r"heading ?(\d)$", name, re.I)
                    level = int(found.group(1)) if found else None
                text = Paragraph(paragraph).text.strip()[:45] if level else ""
                self._outline.append((section, level if text else None, text))
                if "<w:sectPr" in paragraph:
                    section += 1
        return self._outline

    def _paragraph_at(self, offset):
        """The index in `body` of the paragraph holding the body offset `offset`."""
        return next(
            index
            for index, target in enumerate(self.body)
            if target.start <= offset < target.end
        )

    def _chapter_level(self):
        """The heading level that sections most often open with: where notes restart."""
        opens = {}
        for section, level, _ in self._outlined():
            if level and section not in opens:
                opens[section] = level
        levels = list(opens.values())
        return max(set(levels), key=lambda level: (levels.count(level), level)) if levels else None


def _id(attrs):
    found = re.search(r'\bw:id="(-?\d+)"', attrs)
    return found.group(1) if found else None
