"""The map from each note's permanent ID to where the note now stands."""

LABEL = 40  # characters of a note's text that stand for it when it has no label


def map_rows(notes, ids, registry):
    """One (id, label, place, number in the book, heading) per note, in document order."""
    labels = {entry.id: entry.label for entry in registry.entries}
    rows = []
    for note in notes:
        id = ids[note.place]
        label = labels.get(id) or " ".join(note.text.split("\n"))[:LABEL]
        shown = "" if note.shown is None else str(note.shown)
        rows.append((id, label, note.place, shown, note.heading))
    return rows


def map_lines(rows, retired):
    """The map as lines for the terminal."""
    lines = []
    for id, label, place, shown, heading in rows:
        lines.append(f"{id} | {place} | {where(shown, heading)} | {label}")
    if retired:
        lines.append("retired: " + ", ".join(retired))
    return lines


def where(shown, heading):
    """Where the book shows a note: under its heading, with the number it prints."""
    number = f"note {shown}" if shown else "numbered by page"
    return f"{heading}, {number}" if heading else number


def map_markdown(rows, retired, name, save):
    """The map as a Markdown document, regenerated in full at every run."""
    lines = [
        "# Note map",
        "",
        f"Made by note-map from `{name}` (SHA-256 `{save[:16]}`). It is made afresh at every"
        " run: do not edit it.",
        "",
        "| ID | Label | Note | Number in the book | Under |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |")
    lines += ["", "Retired: " + (", ".join(retired) if retired else "none") + "."]
    return "\n".join(lines) + "\n"
