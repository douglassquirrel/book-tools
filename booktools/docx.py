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
        try:
            with zipfile.ZipFile(path) as archive:
                self.entries = [(info, archive.read(info)) for info in archive.infolist()]
        except FileNotFoundError:
            raise DocxError(f"{path}: no such file") from None
        except zipfile.BadZipFile:
            raise DocxError(f"{path}: not a .docx file (it is not a zip archive)") from None
        self._texts = {}
        for info, data in self.entries:
            if WORD_PART.match(info.filename):
                try:
                    self._texts[info.filename] = data.decode("utf-8")
                except UnicodeDecodeError:
                    raise DocxError(f"{path}: {info.filename} is not UTF-8 text") from None
        if "word/document.xml" not in self._texts:
            raise DocxError(f"{path}: not a Word document (it has no word/document.xml)")

    def texts(self):
        """The XML parts directly under word/, as text, by name."""
        return dict(self._texts)

    def write_copy(self, path, replaced):
        """Write a copy at `path` in which the parts named in `replaced` hold the
        given text and every other entry holds the same bytes as here."""
        with zipfile.ZipFile(path, "w") as archive:
            for info, data in self.entries:
                if info.filename in replaced:
                    data = replaced[info.filename].encode("utf-8")
                archive.writestr(info, data)
