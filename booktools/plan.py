"""Places each edit in the manuscript before anything is written."""

from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES
from booktools.paragraph import Paragraph
from booktools.revise import Change
from booktools.trim import common_ends

ORDER = {BODY: 0, ENDNOTES: 1, FOOTNOTES: 2}


class PlanError(Exception):
    """One or more edits cannot be made. `problems` names each."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = problems


class Located:
    """An edit, the paragraph it falls in, and the change to make there."""

    def __init__(self, edit, target, start, end, change):
        self.edit = edit
        self.target = target
        self.start = start  # where the "find" text sits in the paragraph's text
        self.end = end
        self.change = change


def plan(edits, manuscript, highest_id):
    """Return a Located for each edit, in document order, or raise PlanError.

    Revision ids are given out in document order, starting above `highest_id`.
    """
    paragraphs = {}

    def read(target):
        key = (target.part, target.start)
        if key not in paragraphs:
            xml = manuscript.parts[target.part][target.start : target.end]
            paragraphs[key] = Paragraph(xml)
        return paragraphs[key]

    located = []
    for edit in edits:
        matches = [
            (target, start, end)
            for target in manuscript.body
            for start, end in read(target).find(edit.find)
        ]
        target, start, end = matches[0]
        old = read(target).text[start:end]
        prefix, suffix = common_ends(old, edit.replace)
        new = edit.replace[prefix : len(edit.replace) - suffix]
        change = Change(start + prefix, end - suffix, new, after=prefix > 0)
        located.append(Located(edit, target, start, end, change))
    located.sort(key=lambda found: (ORDER[found.target.part], found.target.start, found.start))
    for found in located:
        change = found.change
        if change.start < change.end:
            highest_id += 1
            change.del_id = highest_id
        if change.new:
            highest_id += 1
            change.ins_id = highest_id
    return located
