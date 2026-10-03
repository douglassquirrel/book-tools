"""Finds elements in WordprocessingML by position, without re-serialising anything.

Every function here works on the XML as text and reports offsets into it, so
that a caller can change one paragraph and leave every other byte alone.
"""

import re

# One start, end or empty-element tag. Attribute values are matched as quoted
# strings, so a ">" inside one does not end the tag.
TAG = re.compile(
    r"<(?P<close>/?)(?P<name>[A-Za-z_][\w:.\-]*)"
    r"(?P<attrs>(?:\s+[\w:.\-]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))*)\s*(?P<empty>/?)>"
)


def paragraph_spans(xml):
    """Return (start, end, depth) for every <w:p> element in `xml`, in order of start.

    `depth` is 1 for an ordinary paragraph and more for one nested inside
    another (the text of a text box sits in paragraphs inside a paragraph).
    """
    spans = []
    open_at = []
    for tag in TAG.finditer(xml):
        if tag.group("name") != "w:p":
            continue
        if tag.group("empty"):
            spans.append((tag.start(), tag.end(), len(open_at) + 1))
        elif tag.group("close"):
            index = open_at.pop()
            start, _, depth = spans[index]
            spans[index] = (start, tag.end(), depth)
        else:
            open_at.append(len(spans))
            spans.append((tag.start(), None, len(open_at)))
    return spans


class Node:
    """One element, by its offsets in the text it was parsed from."""

    def __init__(self, name, attrs, start, open_end):
        self.name = name
        self.attrs = attrs  # the raw text of the attributes
        self.start = start  # offset of "<"
        self.open_end = open_end  # offset just after the start tag
        self.close_start = open_end  # offset of the end tag (open_end if empty)
        self.end = open_end  # offset just after the element
        self.children = []


def parse(xml):
    """Parse `xml`, which holds exactly one element, into a tree of Nodes."""
    root = None
    stack = []
    for tag in TAG.finditer(xml):
        if tag.group("close"):
            node = stack.pop()
            node.close_start = tag.start()
            node.end = tag.end()
            continue
        node = Node(tag.group("name"), tag.group("attrs"), tag.start(), tag.end())
        if stack:
            stack[-1].children.append(node)
        elif root is None:
            root = node
        if not tag.group("empty"):
            stack.append(node)
    return root
