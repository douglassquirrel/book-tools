import hashlib

import pytest

from booktools.counts import counts, structure_lines
from booktools.docx import Docx
from tests.docxkit import pack_docx
from tests.samples import W, edited_parts, note, sample_parts, separators

pytestmark = pytest.mark.tier2


def docx(tmp_path, name, parts):
    path = tmp_path / name
    pack_docx(path, parts)
    return Docx(path), hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def test_counts_of_the_sample(tmp_path):
    sample, sha = docx(tmp_path, "sample.docx", sample_parts())
    assert counts(sample) == {
        "sha256": sha,
        "revision": "3",
        "modified": "2026-10-01T09:00:00Z",
        "paragraphs": 9,
        "tracked changes": 0,
        "trackRevisions": False,
        "comments": 0,
        "endnote markers": 2,
        "endnotes": 2,
        "footnote markers": 1,
        "footnotes": 1,
        "straight quotes": 0,
        "links in notes": 0,
        "highlighted runs": 0,
        "notes of more than one paragraph": [],
    }


def busy_parts():
    """A save with one of everything the counts look for."""
    parts = sample_parts()
    body = (
        '<w:p><w:r><w:t>He said "no" and it&apos;s done.</w:t></w:r>'
        '<w:ins w:id="5" w:author="E"><w:r><w:t>new</w:t></w:r></w:ins>'
        '<w:del w:id="6" w:author="E"><w:r><w:delText>old</w:delText></w:r></w:del>'
        '<w:moveFrom w:id="7"><w:r><w:t>m</w:t></w:r></w:moveFrom>'
        '<w:moveTo w:id="8"><w:r><w:t>m</w:t></w:r></w:moveTo>'
        '<w:r><w:rPr><w:highlight w:val="yellow"/></w:rPr><w:t>lit</w:t></w:r>'
        '<w:r><w:rPr><w:highlight w:val="white"/></w:rPr><w:t>lit</w:t></w:r>'
        '<w:r><w:commentReference w:id="0"/></w:r>'
        '<w:r><w:endnoteReference w:id="1"/></w:r><w:r><w:endnoteReference w:id="2"/></w:r>'
        '<w:r><w:endnoteReference w:id="3"/></w:r></w:p>'
    )
    parts["word/document.xml"] = f"<w:document {W}><w:body>{body}<w:sectPr/></w:body></w:document>"
    two = note("endnote", 2, "First.").replace(
        "</w:p></w:endnote>", "</w:p><w:p><w:r><w:t>Second ‘curly’.</w:t></w:r></w:p></w:endnote>"
    )
    linked = note("endnote", 1, "See").replace(
        "</w:p></w:endnote>",
        '<w:hyperlink r:id="rId9"><w:r><w:t>it\'s</w:t></w:r></w:hyperlink></w:p></w:endnote>',
    )
    parts["word/endnotes.xml"] = f"<w:endnotes {W}>" + separators("endnote") + linked + two + "</w:endnotes>"
    parts["word/settings.xml"] = f"<w:settings {W}><w:trackRevisions/></w:settings>"
    parts["word/comments.xml"] = f"<w:comments {W}/>"
    del parts["docProps/core.xml"]
    return parts


def test_counts_everything_it_is_asked_to_look_for(tmp_path):
    busy, _ = docx(tmp_path, "busy.docx", busy_parts())
    found = counts(busy)
    del found["sha256"]
    assert found == {
        "revision": "",
        "modified": "",
        "paragraphs": 1,
        "tracked changes": 4,
        "trackRevisions": True,
        "comments": 1,
        "endnote markers": 3,
        "endnotes": 2,
        "footnote markers": 0,
        "footnotes": 1,
        "straight quotes": 4,
        "links in notes": 1,
        "highlighted runs": 2,
        "notes of more than one paragraph": ["endnote 2"],
    }


def test_the_structure_section_sets_the_two_saves_side_by_side(tmp_path):
    old, old_sha = docx(tmp_path, "old.docx", sample_parts())
    new, new_sha = docx(tmp_path, "new.docx", edited_parts())
    assert structure_lines(old, new) == [
        "== Structure and counts (old | new)",
        f"sha256: {old_sha} | {new_sha}",
        "revision: 3 | 4",
        "modified (London time): 2026-10-01 10:00 | 2026-10-02 18:30",
        "parts that differ: word/document.xml, word/endnotes.xml, docProps/core.xml",
        "media: the same 1 file",
        "paragraphs: 9 | 10 (+1)",
        "tracked changes: 0 | 0",
        "trackRevisions: off | off",
        "comments: 0 | 0",
        "endnote markers: 2 | 3 (+1)",
        "endnotes: 2 | 3 (+1)",
        "footnote markers: 1 | 1",
        "footnotes: 1 | 1",
        "straight quotes: 0 | 0",
        "links in notes: 0 | 0",
        "highlighted runs: 0 | 0",
        "notes of more than one paragraph: none | none",
    ]
    assert structure_lines(old, new, utc=True)[3] == (
        "modified (UTC): 2026-10-01 09:00 | 2026-10-02 17:30"
    )


def test_the_structure_section_names_parts_and_pictures_only_one_save_has(tmp_path):
    old, _ = docx(tmp_path, "old.docx", sample_parts())
    parts = busy_parts()
    parts["word/media/image2.png"] = b"another"
    del parts["word/media/image1.png"]
    new, _ = docx(tmp_path, "new.docx", parts)
    lines = structure_lines(old, new)
    assert lines[2:6] == [
        "revision: 3 | ",
        "modified (London time): 2026-10-01 10:00 | ",
        "parts that differ: word/document.xml, word/endnotes.xml, word/settings.xml,"
        " word/comments.xml (new only), docProps/core.xml (old only)",
        "media: removed image1.png; added image2.png",
    ]
    assert lines[6] == "paragraphs: 9 | 1 (-8)"
    assert lines[8] == "trackRevisions: off | on"
    assert lines[-1] == "notes of more than one paragraph: none | endnote 2"
