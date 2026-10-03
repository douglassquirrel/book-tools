"""The notes of one save of a manuscript, as note-map knows them."""

from booktools.manuscript import ENDNOTES, FOOTNOTES
from booktools.paragraph import Paragraph
from booktools.text import nfc


class Note:
    def __init__(self, kind, number, text, sentence, heading, shown):
        self.kind = kind  # "endnote" or "footnote"
        self.number = number  # its position among notes of its kind, from 1
        self.text = text  # the note's own text
        self.sentence = sentence  # the sentence its marker sits in
        self.heading = heading  # the heading it falls under, or ""
        self.shown = shown  # the number the book prints, or None if that cannot be known

    @property
    def place(self):
        return f"{self.kind}:{self.number}"


def read_notes(manuscript):
    """Every note of `manuscript`, a Manuscript: endnotes in order, then footnotes."""
    notes = []
    for kind, part, each in (
        ("endnote", ENDNOTES, manuscript.endnotes),
        ("footnote", FOOTNOTES, manuscript.footnotes),
    ):
        xml = manuscript.parts.get(part, "")
        for number, targets in enumerate(each, 1):
            paragraphs = [Paragraph(xml[t.start : t.end]).text.strip() for t in targets]
            heading, shown = manuscript.note_place(kind, number)
            notes.append(
                Note(
                    kind,
                    number,
                    nfc("\n".join(paragraphs).strip()),
                    nfc(manuscript.marker_sentence(kind, number)),
                    heading,
                    shown,
                )
            )
    return notes
