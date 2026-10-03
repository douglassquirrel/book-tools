"""One paragraph as its reader sees it: the text of its runs joined, and where each
character sits in the XML."""

import html
import re

from booktools.xmlscan import parse

# One character of text as the XML spells it: an entity or a single character.
UNIT = re.compile(r"&[^;]+;|.", re.S)


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
        self._length = 0
        self._walk(parse(xml))
        self.text = "".join(html.unescape(u) for p in self.pieces for u in p.units)

    def _walk(self, node):
        for child in node.children:
            if child.name == "w:r":
                self._run(child)

    def _run(self, run):
        for child in run.children:
            if child.name == "w:t":
                units = UNIT.findall(self.xml[child.open_end : child.close_start])
                self.pieces.append(Piece(run, child, self._length, units))
                self._length += len(units)
