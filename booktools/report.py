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
