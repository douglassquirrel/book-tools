"""The reading text of a manuscript: pandoc's markdown with each note named by its
permanent ID in place of pandoc's number."""

import re

NOTE = re.compile(r"^\[\^(\d+)\]:[ ]?", re.M)
MARKER = re.compile(r"\[\^(\d+)\]")


class ExtractError(Exception):
    """pandoc's text cannot be given IDs with certainty."""


def reading_text(markdown, order, name, save):
    """`markdown`, pandoc's reading of a save, with each note's permanent ID in place
    of pandoc's number, at the marker and at the note, under a line saying which save
    it came from.

    `order` holds (ID, where the book shows the note) for every note of the save in
    the one sequence pandoc counts them in: as their markers come, endnotes and
    footnotes together. Raises ExtractError if pandoc's notes do not tally with it.
    """
    read = len(set(NOTE.findall(markdown)))
    if read != len(order):
        notes = "1 note" if read == 1 else f"{read} notes"
        raise ExtractError(f"pandoc read {notes} where the manuscript has {len(order)}")

    def note(found):
        id, where = order[int(found.group(1)) - 1]
        return f"[^{id}]: <!-- {where} --> "

    def marker(found):
        number = int(found.group(1))
        if not 1 <= number <= len(order):
            raise ExtractError(
                f"pandoc's text has a marker [^{number}] and only {len(order)} notes"
            )
        return f"[^{order[number - 1][0]}]"

    text = MARKER.sub(marker, NOTE.sub(note, markdown))
    return (
        f"<!-- Made by note-map from `{name}` (SHA-256 `{save[:16]}`), for reading only:"
        f" each note is named by its permanent ID. Do not edit it. -->\n\n{text}"
    )
