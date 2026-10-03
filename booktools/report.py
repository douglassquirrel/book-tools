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
    old = text[change.start : change.end]
    if old and change.new:
        shown = f"{old} {ARROW} {change.new}"
    else:
        shown = f"{old} {ARROW}" if old else f"{ARROW} {change.new}"
    before = text[max(0, change.start - CONTEXT) : change.start]
    after = text[change.end : change.end + CONTEXT]
    lead = ELLIPSIS if change.start > CONTEXT else ""
    trail = ELLIPSIS if change.end + CONTEXT < len(text) else ""
    name = found.edit.id or f"edit {found.edit.index}"
    why = f" {found.edit.why} " if found.edit.why else " "
    return f"{name} | {place} | {lead}{before}[{shown}]{after}{trail} |{why}| {status}"
