"""Builds the tiny .docx files the tests use, from hand-written XML."""

import zipfile

FIXED_TIME = (2000, 1, 1, 0, 0, 0)


def pack_docx(path, parts, compress=True):
    """Write a .docx at `path` holding `parts`, a mapping of entry name to str or bytes.

    Entries are written in the order given, with a fixed timestamp, so the same
    parts always give the same bytes. Files kept in the repository are written
    with `compress=False`, so that they do not depend on the version of zlib.
    """
    with zipfile.ZipFile(path, "w") as z:
        for name, data in parts.items():
            if isinstance(data, str):
                data = data.encode("utf-8")
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
