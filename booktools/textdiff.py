"""The difference in words between two saves, body and notes, from pandoc's reading."""

import difflib
import re

from booktools.report import change_shown

NOTE = re.compile(r"^\[\^(\d+)\]: (.*)")
REFERENCE = re.compile(r"\[\^\d+\]")
WORD = re.compile(r"\S+\s*|\s+")  # a word with the space after it
LONG = 200  # a changed line longer than this is shown as its changed words only


def text_diff(old, new, full=False):
    """The lines reporting what changed between two pandoc markdown texts.

    Body lines are compared with note references made alike, so that renumbering
    alone is not a change; notes are compared in order, and each change gives the
    old and new note numbers. A line or note of more than LONG characters that was
    changed is shown as its changed words only, unless `full`.
    """
    old_body, old_notes = _split(old)
    new_body, new_notes = _split(new)
    lines = []
    matcher = difflib.SequenceMatcher(
        None, [_alike(line) for line in old_body], [_alike(line) for line in new_body],
        autojunk=False,
    )
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            lines.append(f"=== BODY {tag}")
            lines.extend(_block(old_body[i1:i2], new_body[j1:j2], full))
    was = [old_notes[number] for number in sorted(old_notes)]
    now = [new_notes[number] for number in sorted(new_notes)]
    matcher = difflib.SequenceMatcher(None, was, now, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            old_numbers = list(range(i1 + 1, i2 + 1))
            new_numbers = list(range(j1 + 1, j2 + 1))
            lines.append(f"=== NOTES {tag} old {old_numbers} new {new_numbers}")
            lines.extend(_block(was[i1:i2], now[j1:j2], full))
    return lines


def _block(old, new, full):
    """The lines showing that the lines `old` gave way to the lines `new`."""
    whole = [f"  OLD: {line}" for line in old] + [f"  NEW: {line}" for line in new]
    if full or len(old) != len(new):
        return whole
    short = [_changed_words(was, now) for was, now in zip(old, new)]
    if not any(short):
        return whole
    lines = []
    for was, now, changed in zip(old, new, short):
        lines.extend(changed or [f"  OLD: {was}", f"  NEW: {now}"])
    return lines


def _changed_words(old, new):
    """One line for each run of words that differs between two versions of a long
    line, each with the words around it; None if neither is long, or if those lines
    would together be longer than the two versions in full."""
    if max(len(old), len(new)) <= LONG:
        return None
    was, now = WORD.findall(old), WORD.findall(new)
    starts = [0]
    for word in was:
        starts.append(starts[-1] + len(word))
    matcher = difflib.SequenceMatcher(
        None, [_alike(word) for word in was], [_alike(word) for word in now], autojunk=False
    )
    lines = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        gone, come = "".join(was[i1:i2]), "".join(now[j1:j2])
        end = starts[i2]
        # The space after a replaced word is not part of the change.
        while gone and come and gone[-1].isspace() and gone[-1] == come[-1]:
            gone, come, end = gone[:-1], come[:-1], end - 1
        lines.append("  CHANGED: " + change_shown(old, starts[i1], end, come))
    if sum(len(line) for line in lines) > len(old) + len(new):
        return None
    return lines


def _split(text):
    """(the body's lines, {note number: note text}) of a pandoc markdown text."""
    body, notes = [], {}
    for line in text.split("\n"):
        found = NOTE.match(line)
        if found:
            notes[int(found.group(1))] = found.group(2)
        elif line.strip():
            # Blank lines are left out: one comes and goes with every note.
            body.append(line)
    return body, notes


def _alike(line):
    """A body line with every note reference made the same, so that a note's number
    changing is not a change to the line."""
    return REFERENCE.sub("[^n]", line)
