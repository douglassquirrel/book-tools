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
    problems = []
    for edit in edits:
        space, where = _space(edit, manuscript)
        if space is None:
            problems.append(f"{edit.name}: {where}")
            continue
        matches = [
            (target, start, end) for target in space for start, end in read(target).find(edit.find)
        ]
        fault = _unusable(edit, matches, where)
        if fault:
            problems.append(f"{edit.name}: {fault}")
            continue
        target, start, end = matches[(edit.occurrence or 1) - 1]
        obstacle = read(target).obstacle(start, end)
        if obstacle:
            advice = (
                "accept or reject that change in Word first"
                if obstacle.startswith("touches")
                else "make the edit on one side of it"
            )
            problems.append(f'{edit.name}: the "find" text {obstacle}; {advice}')
            continue
        old = read(target).text[start:end]
        prefix, suffix = common_ends(old, edit.replace)
        new = edit.replace[prefix : len(edit.replace) - suffix]
        change = Change(start + prefix, end - suffix, new, after=prefix > 0)
        located.append(Located(edit, target, start, end, change))
    if problems:
        raise PlanError(problems)
    located.sort(
        key=lambda found: (
            ORDER[found.target.part],
            found.target.note,
            found.target.start,
            found.start,
        )
    )
    for found in located:
        change = found.change
        if change.start < change.end:
            highest_id += 1
            change.del_id = highest_id
        if change.new:
            highest_id += 1
            change.ins_id = highest_id
    return located


def _space(edit, manuscript):
    """The paragraphs to search for `edit` and what to call them; (None, why) if none."""
    kind = edit.where[0]
    if kind == "body":
        return manuscript.body, "the body"
    notes = {"endnote": manuscript.endnotes, "footnote": manuscript.footnotes}
    if kind == "all":
        space = list(manuscript.body)
        for note in manuscript.endnotes + manuscript.footnotes:
            space.extend(note)
        return space, "the body or the notes"
    number = edit.where[1]
    if number > len(notes[kind]):
        count = len(notes[kind])
        has = "no" if count == 0 else str(count)
        plural = "" if count == 1 else "s"
        return None, f"there is no {kind}:{number} (the document has {has} {kind}{plural})"
    return notes[kind][number - 1], f"{kind}:{number}"


def _unusable(edit, matches, where):
    """Why the matches found for `edit` do not single out one place, or None."""
    if not matches:
        return f'"find" text not found in {where}'
    count = "once" if len(matches) == 1 else f"{len(matches)} times"
    if edit.occurrence is None and len(matches) > 1:
        numbers = [str(target.number) for target, _, _ in matches]
        listed = ", ".join(numbers[:-1]) + " and " + numbers[-1]
        return (
            f'"find" text occurs {count} in {where} (paragraphs {listed});'
            ' add "occurrence" to say which'
        )
    if edit.occurrence is not None and edit.occurrence > len(matches):
        return f'"occurrence" is {edit.occurrence} but the "find" text occurs {count} in {where}'
    return None
