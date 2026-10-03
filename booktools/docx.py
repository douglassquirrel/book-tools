"""Reads a .docx and writes a copy of it with some parts replaced."""

import re
import zipfile

WORD_PART = re.compile(r"word/[^/]+\.xml$")


class DocxError(Exception):
    """The file cannot be used as a .docx."""


class Docx:
    """The entries of a .docx, in order, exactly as stored."""

    def __init__(self, path):
        self.path = path
        with zipfile.ZipFile(path) as archive:
            self.entries = [(info, archive.read(info)) for info in archive.infolist()]

    def texts(self):
        """The XML parts directly under word/, as text, by name."""
        return {
            info.filename: data.decode("utf-8")
            for info, data in self.entries
            if WORD_PART.match(info.filename)
        }

    def write_copy(self, path, replaced):
        """Write a copy at `path` in which the parts named in `replaced` hold the
        given text and every other entry holds the same bytes as here."""
        with zipfile.ZipFile(path, "w") as archive:
            for info, data in self.entries:
                if info.filename in replaced:
                    data = replaced[info.filename].encode("utf-8")
                archive.writestr(info, data)
