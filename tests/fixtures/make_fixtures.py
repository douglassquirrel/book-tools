"""Regenerates the sample documents in this folder: python3 -m tests.fixtures.make_fixtures

The text is invented. A test checks that the committed files are exactly what
this script makes.
"""

import json
from pathlib import Path

from tests.docxkit import pack_docx
from tests.samples import SAMPLE_EDITS, edited_parts, sample_parts


def build(folder):
    """Write sample.docx, sample-edited.docx and edits.json into `folder`."""
    folder = Path(folder)
    pack_docx(folder / "sample.docx", sample_parts(), compress=False)
    pack_docx(folder / "sample-edited.docx", edited_parts(), compress=False)
    text = json.dumps(SAMPLE_EDITS, indent=2, ensure_ascii=False) + "\n"
    (folder / "edits.json").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    build(Path(__file__).parent)
