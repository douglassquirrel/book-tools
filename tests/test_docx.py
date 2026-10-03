import zipfile

import pytest

from booktools.docx import Docx
from tests.docxkit import pack_docx

pytestmark = pytest.mark.tier2

PARTS = {
    "[Content_Types].xml": "<Types/>",
    "_rels/.rels": "<Relationships/>",
    "word/document.xml": '<?xml version="1.0"?>\r\n<w:document>café</w:document>',
    "word/styles.xml": "<w:styles/>",
    "word/media/image1.png": b"\x89PNG\x00\xff",
    "word/_rels/document.xml.rels": "<Relationships/>",
    "docProps/core.xml": "<cp:coreProperties/>",
}


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "in.docx"
    pack_docx(path, PARTS)
    return path


def test_reads_every_entry_in_order_and_the_word_parts_as_text(sample):
    docx = Docx(sample)
    assert [info.filename for info, _ in docx.entries] == list(PARTS)
    assert docx.entries[4][1] == b"\x89PNG\x00\xff"
    assert docx.texts() == {
        "word/document.xml": PARTS["word/document.xml"],  # the CRLF is kept
        "word/styles.xml": "<w:styles/>",
    }


def test_a_copy_differs_only_in_the_parts_replaced(sample, tmp_path):
    before = sample.read_bytes()
    out = tmp_path / "out.docx"
    Docx(sample).write_copy(out, {"word/document.xml": "<w:document>thé</w:document>"})
    assert sample.read_bytes() == before
    with zipfile.ZipFile(sample) as old, zipfile.ZipFile(out) as new:
        assert new.namelist() == old.namelist()
        for name in old.namelist():
            a, b = old.getinfo(name), new.getinfo(name)
            assert (a.date_time, a.compress_type, a.external_attr) == (
                b.date_time, b.compress_type, b.external_attr,
            )
            if name == "word/document.xml":
                assert new.read(name) == "<w:document>thé</w:document>".encode()
            else:
                assert new.read(name) == old.read(name)
