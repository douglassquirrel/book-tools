"""Places each edit in the manuscript before anything is written."""

import unicodedata

from booktools.manuscript import BODY, ENDNOTES, FOOTNOTES
from booktools.paragraph import Paragraph
from booktools.revise import Change
from booktools.trim import difference

ORDER = {BODY: 0, ENDNOTES: 1, FOOTNOTES: 2}


class PlanError(Exception):
    """One or more edits cannot be made. `problems` names each."""

    def __init__(self, problems, located=()):
        super().__init__("; ".join(problems))
        self.problems = problems
        self.located = list(located)  # the edits that could be placed, in document order


class Located:
    """An edit, the paragraph it falls in, and the change to make there."""

    def __init__(self, edit, target, start, end, change, text):
        self.text = text  # the paragraph's text before the change
        self.edit = edit
        self.target = target
        self.start = start  # where the "find" text sits in the paragraph's text
        self.end = end
        self.change = change


def plan(edits, manuscript, highest_id, ids=None):
    """Return a Located for each edit, in document order, or raise PlanError.

    Revision ids are given out in document order, starting above `highest_id`.
    `ids` says where each note named by its permanent ID now is: {ID: (kind, number)},
    or {ID: why it cannot be placed} (`registry.where_now` gives it).
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
        space, where = _space(edit, manuscript, ids or {})
        if space is None:
            problems.append(f"{edit.name}: {where}")
            continue
        matches = [
            (target, start, end) for target in space for start, end in read(target).find(edit.find)
        ]
        fault = _unusable(edit, matches, where) if matches else _missing(edit, space, where, read)
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
        first, last, new = difference(old, edit.replace)
        change = Change(start + first, start + last, new, after=first > 0)
        located.append(Located(edit, target, start, end, change, read(target).text))
    located.sort(
        key=lambda found: (
            ORDER[found.target.part],
            found.target.note,
            found.target.start,
            found.start,
        )
    )
    for found, problem in _overlaps(located):
        problems.append(problem)
        if found in located:
            located.remove(found)
    if problems:
        raise PlanError(problems, located)
    for found in located:
        change = found.change
        if change.start < change.end:
            highest_id += 1
            change.del_id = highest_id
        if change.new:
            highest_id += 1
            change.ins_id = highest_id
    return located


def _overlaps(located):
    """(edit, problem) for each edit whose "find" text shares characters with that of
    an edit earlier in the edits file."""
    problems = []
    in_file_order = sorted(located, key=lambda found: found.edit.index)
    for index, later in enumerate(in_file_order):
        for earlier in in_file_order[:index]:
            same = (earlier.target.part, earlier.target.start) == (
                later.target.part,
                later.target.start,
            )
            if same and earlier.start < later.end and later.start < earlier.end:
                where = later.target.place
                where = "the body" if where == "body" else where
                problems.append(
                    (
                        later,
                        f"{later.edit.name}: overlaps {earlier.edit.name} in paragraph"
                        f" {later.target.number} of {where}; combine them into one edit",
                    )
                )
    return problems


def _space(edit, manuscript, ids):
    """The paragraphs to search for `edit` and what to call them; (None, why) if none."""
    kind = edit.where[0]
    if kind == "id":
        id = edit.where[1]
        now = ids.get(id, f"{id} cannot be placed: no registry was given")
        if isinstance(now, str):
            return None, now
        kind, number = now
        notes = manuscript.endnotes if kind == "endnote" else manuscript.footnotes
        return notes[number - 1], f"{id} ({kind}:{number})"
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


def _missing(edit, space, where, read):
    """Why nothing matched: the text runs across two paragraphs, or is not there."""
    nfc = unicodedata.normalize
    wanted = nfc("NFC", edit.find)
    for first, second in zip(space, space[1:]):
        if first.part != second.part:
            continue
        for gap in ("", " "):
            if wanted in nfc("NFC", read(first).text + gap + read(second).text):
                place = "the body" if first.place == "body" else first.place
                return (
                    f'"find" text runs from paragraph {first.number} into paragraph'
                    f" {second.number} of {place}; an edit must stay within one paragraph"
                    " (join or split paragraphs by hand in Word)"
                )
    return f'"find" text not found in {where}'


def _unusable(edit, matches, where):
    """Why the matches found for `edit` do not single out one place, or None."""
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
