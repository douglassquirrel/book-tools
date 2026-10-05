"""The lines propose-edits prints: one per edit, for the author to read beside Word."""

CONTEXT = 25  # characters shown either side of a change
ARROW = "\N{RIGHTWARDS ARROW}"
ELLIPSIS = "\N{HORIZONTAL ELLIPSIS}"


def edit_line(found, text, place, status):
    """One line for one edit: its id, where it is, the words around it with the
    change shown as [old → new], its reason, and `status`.

    `text` is the paragraph's text before the change; `place` says where the
    paragraph is, in the author's terms.
    """
    change = found.change
    shown = change_shown(text, change.start, change.end, change.new)
    name = found.edit.id or f"edit {found.edit.index}"
    why = f" {found.edit.why} " if found.edit.why else " "
    return f"{name} | {place} | {shown} |{why}| {status}"


def change_shown(text, start, end, new):
    """A change to `text` with the words around it: its characters from `start` to `end`
    giving way to `new`, as …25 characters[old → new]25 characters…"""
    old = text[start:end]
    if old and new:
        shown = f"{old} {ARROW} {new}"
    else:
        shown = f"{old} {ARROW}" if old else f"{ARROW} {new}"
    before = text[max(0, start - CONTEXT) : start]
    after = text[end : end + CONTEXT]
    lead = ELLIPSIS if start > CONTEXT else ""
    trail = ELLIPSIS if end + CONTEXT < len(text) else ""
    return f"{lead}{before}[{shown}]{after}{trail}"


MARKS = ",;:.!?"
NEAR = 10  # characters shown either side of the place a note is about


def edge_notes(found, text):
    """Lines warning of what accepting one edit would leave where the changed words
    meet their neighbours: two spaces in a row, a punctuation mark doubled, a space
    before a punctuation mark, none after one, or two words run together. `text` is
    the paragraph before the change. Only what the edit brings about is noted, not
    what was already so beside it.
    """
    change = found.change
    accepted = text[: change.start] + change.new + text[change.end :]
    was = {
        _fault(text[at - 1], text[at])
        for at in (change.start, change.end)
        if 0 < at < len(text)
    }
    name = found.edit.id or f"edit {found.edit.index}"
    lines = []
    for edge in sorted({change.start, change.start + len(change.new)}):
        if not 0 < edge < len(accepted):
            continue
        fault = _fault(accepted[edge - 1], accepted[edge])
        if fault and fault not in was:
            lead = ELLIPSIS if edge > NEAR else ""
            trail = ELLIPSIS if edge + NEAR < len(accepted) else ""
            near = accepted[max(0, edge - NEAR) : edge + NEAR]
            lines.append(f'note: accepting {name} {fault}: "{lead}{near}{trail}"')
    return lines


def _fault(before, after):
    """What is wrong with two characters standing side by side, or None."""
    if before == " " and after == " ":
        return "leaves two spaces in a row"
    if before in MARKS and before == after:
        return "leaves a punctuation mark doubled"
    if before == " " and after in MARKS:
        return "leaves a space before a punctuation mark"
    if before in MARKS and after.isalnum():
        return "leaves no space after a punctuation mark"
    if before.isalnum() and after.isalnum():
        return "runs two words together"
    return None
