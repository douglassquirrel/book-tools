"""The difference in words between two saves, body and notes, from pandoc's reading."""

import difflib
import re

NOTE = re.compile(r"^\[\^(\d+)\]: (.*)")
REFERENCE = re.compile(r"\[\^\d+\]")
PANDOC = ["pandoc", "-f", "docx", "-t", "markdown-smart", "--wrap=none"]


def text_diff(old, new):
    """The lines reporting what changed between two pandoc markdown texts.

    Body lines are compared with note references made alike, so that renumbering
    alone is not a change; notes are compared in order, and each change gives the
    old and new note numbers.
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
            lines.extend(f"  OLD: {line}" for line in old_body[i1:i2])
            lines.extend(f"  NEW: {line}" for line in new_body[j1:j2])
    was = [old_notes[number] for number in sorted(old_notes)]
    now = [new_notes[number] for number in sorted(new_notes)]
    matcher = difflib.SequenceMatcher(None, was, now, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            old_numbers = list(range(i1 + 1, i2 + 1))
            new_numbers = list(range(j1 + 1, j2 + 1))
            lines.append(f"=== NOTES {tag} old {old_numbers} new {new_numbers}")
            lines.extend(f"  OLD: {note}" for note in was[i1:i2])
            lines.extend(f"  NEW: {note}" for note in now[j1:j2])
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
