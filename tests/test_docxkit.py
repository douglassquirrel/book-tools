import zipfile

import pytest

from tests.docxkit import pack_docx

pytestmark = pytest.mark.tier1

PARTS = {
    "[Content_Types].xml": "<Types/>",
    "word/document.xml": "<w:document>caf\u00e9 — “quoted”</w:document>",
    "word/media/image1.png": b"\x89PNG\x00\xff",
}


def test_packs_each_part_in_order_with_its_exact_bytes(tmp_path):
    out = tmp_path / "a.docx"
    pack_docx(out, PARTS)
    with zipfile.ZipFile(out) as z:
        assert z.namelist() == list(PARTS)
        assert z.read("word/document.xml") == PARTS["word/document.xml"].encode("utf-8")
        assert z.read("word/media/image1.png") == b"\x89PNG\x00\xff"


def test_packing_the_same_parts_twice_gives_identical_files(tmp_path):
    pack_docx(tmp_path / "a.docx", PARTS)
    pack_docx(tmp_path / "b.docx", PARTS)
    assert (tmp_path / "a.docx").read_bytes() == (tmp_path / "b.docx").read_bytes()
