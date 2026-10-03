import zipfile

import pytest

from booktools.docx import Docx
from tests.docxkit import pack_docx

pytestmark = pytest.mark.tier2

PARTS = {
    "[Content_Types].xml": "<Types/>",
    "_rels/.rels": "<Relationships/>",
    "word/document.xml": '<?xml version="1.0"?>\r\n<w:document>caf\u00e9</w:document>',
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
    Docx(sample).write_copy(out, {"word/document.xml": "<w:document>th\u00e9</w:document>"})
    assert sample.read_bytes() == before
    with zipfile.ZipFile(sample) as old, zipfile.ZipFile(out) as new:
        assert new.namelist() == old.namelist()
        for name in old.namelist():
            a, b = old.getinfo(name), new.getinfo(name)
            assert (a.date_time, a.compress_type, a.external_attr) == (
                b.date_time, b.compress_type, b.external_attr,
            )
            if name == "word/document.xml":
                assert new.read(name) == "<w:document>th\u00e9</w:document>".encode()
            else:
                assert new.read(name) == old.read(name)


def refusal(path):
    from booktools.docx import DocxError

    with pytest.raises(DocxError) as caught:
        Docx(path)
    return str(caught.value)


def test_a_file_that_is_missing_or_not_a_docx_is_refused_in_words(tmp_path):
    assert refusal(tmp_path / "none.docx") == f"{tmp_path / 'none.docx'}: no such file"
    text = tmp_path / "notes.docx"
    text.write_text("just text")
    assert refusal(text) == f"{text}: not a .docx file (it is not a zip archive)"
    other = tmp_path / "other.docx"
    pack_docx(other, {"mimetype": "application/epub+zip"})
    assert refusal(other) == f"{other}: not a Word document (it has no word/document.xml)"
    odd = tmp_path / "odd.docx"
    pack_docx(odd, {"word/document.xml": "<w:document>caf\u00e9</w:document>".encode("utf-16")})
    assert refusal(odd) == f"{odd}: word/document.xml is not UTF-8 text"


def test_names_the_first_entry_of_a_copy_that_is_not_the_same_bytes(sample, tmp_path):
    original = Docx(sample)
    same = tmp_path / "same.docx"
    original.write_copy(same, {"word/document.xml": "<w:document>new</w:document>"})
    assert original.strayed(Docx(same), {"word/document.xml"}) is None
    assert original.strayed(Docx(same), set()) == "word/document.xml"
    fewer = tmp_path / "fewer.docx"
    pack_docx(fewer, {k: v for k, v in PARTS.items() if k != "docProps/core.xml"})
    assert original.strayed(Docx(fewer), set()) == "the list of entries"
