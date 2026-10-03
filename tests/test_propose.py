import pytest

from booktools.editsfile import Edit
from booktools.manuscript import BODY, ENDNOTES, Manuscript
from booktools.plan import plan
from booktools.propose import apply

pytestmark = pytest.mark.tier1

DATES = ("2026-10-03T14:46:00Z", "2026-10-03T13:46:00Z")
W16DU = 'xmlns:w16du="http://schemas.microsoft.com/office/word/2023/wordml/word16du"'
LOCAL = ' w:author="Claude" w:date="2026-10-03T14:46:00Z"'
BOTH = LOCAL + ' w16du:dateUtc="2026-10-03T13:46:00Z"'


def p(text):
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


HEAD = f'<?xml version="1.0"?>\r\n<w:document {W16DU}><w:body>'
UNTOUCHED = p("untouched &amp; unchanged") + '<w:p><w:r><w:endnoteReference w:id="1"/></w:r></w:p>'
TAIL = "<w:sectPr/></w:body></w:document>"
PARTS = {
    BODY: HEAD + p("the quick brown fox") + UNTOUCHED + TAIL,
    ENDNOTES: '<w:endnotes><w:endnote w:id="1">' + p("a note") + "</w:endnote></w:endnotes>",
    "word/styles.xml": "<w:styles/>",
}


def edit(index, find, replace, where=("body",)):
    return Edit(index, "", where, find, replace, None, "")


def proposed(edits):
    located = plan(edits, Manuscript(PARTS), highest_id=0)
    return apply(PARTS, located, "Claude", DATES)


def test_makes_every_change_and_leaves_all_else_byte_for_byte():
    out = proposed(
        [edit(1, "fox", "dog"), edit(2, "quick", "slow"), edit(3, "a note", "the note", ("endnote", 1))]
    )
    assert out[BODY] == (
        HEAD
        + '<w:p><w:r><w:t xml:space="preserve">the </w:t></w:r>'
        f'<w:del w:id="1"{BOTH}><w:r><w:delText>quick</w:delText></w:r></w:del>'
        f'<w:ins w:id="2"{BOTH}><w:r><w:t>slow</w:t></w:r></w:ins>'
        '<w:r><w:t xml:space="preserve"> brown </w:t></w:r>'
        f'<w:del w:id="3"{BOTH}><w:r><w:delText>fox</w:delText></w:r></w:del>'
        f'<w:ins w:id="4"{BOTH}><w:r><w:t>dog</w:t></w:r></w:ins></w:p>'
        + UNTOUCHED
        + TAIL
    )
    # The endnotes part does not declare w16du, so the UTC attribute is left out there.
    assert out[ENDNOTES] == (
        '<w:endnotes><w:endnote w:id="1"><w:p>'
        f'<w:del w:id="5"{LOCAL}><w:r><w:delText>a</w:delText></w:r></w:del>'
        f'<w:ins w:id="6"{LOCAL}><w:r><w:t>the</w:t></w:r></w:ins>'
        '<w:r><w:t xml:space="preserve"> note</w:t></w:r></w:p></w:endnote></w:endnotes>'
    )
    assert out["word/styles.xml"] == "<w:styles/>"
    assert PARTS[BODY] == HEAD + p("the quick brown fox") + UNTOUCHED + TAIL  # input not altered


def test_the_author_s_name_is_escaped_in_the_attribute():
    located = plan([edit(1, "fox", "dog")], Manuscript(PARTS), highest_id=0)
    out = apply(PARTS, located, 'R&D "Ed" <x>', DATES)
    assert 'w:author="R&amp;D &quot;Ed&quot; &lt;x&gt;"' in out[BODY]


EDITS = [edit(1, "fox", "dog"), edit(2, "quick", "slow"), edit(3, "a note", "the note", ("endnote", 1))]


def checked(tamper=None, edits=EDITS):
    """Verify a copy, after `tamper` (part, old, new) has spoilt it if given."""
    from booktools.propose import verify

    located = plan(edits, Manuscript(PARTS), highest_id=0)
    out = apply(PARTS, located, "Claude", DATES)
    if tamper:
        part, old, new = tamper
        assert old in out[part]
        out[part] = out[part].replace(old, new, 1)
    return verify(PARTS, out, located, "Claude", DATES)


def failed(results):
    return [name for name, passed, _ in results if not passed]


def test_a_sound_copy_passes_all_four_checks():
    assert checked() == [
        ("reject all", True, "every paragraph reads as in the original"),
        ("accept all", True, "the original with exactly the 3 edits made"),
        ("revisions", True, "6 revisions for 3 edits, all by Claude at 2026-10-03T14:46:00Z"),
        ("package", True, "2 parts changed, each well-formed; everything else byte-identical"),
    ]


def test_reject_all_fails_when_text_outside_the_revisions_was_altered():
    results = checked((BODY, "untouched &amp; unchanged", "untouched &amp; changed"))
    assert "reject all" in failed(results)
    assert results[0] == (
        "reject all",
        False,
        "paragraph 2 of word/document.xml reads 'untouched & changed'"
        " but the original reads 'untouched & unchanged'",
    )


def test_reject_all_fails_when_a_deleted_word_is_not_the_original_word():
    results = checked((BODY, "<w:delText>quick</w:delText>", "<w:delText>quack</w:delText>"))
    assert results[0][:2] == ("reject all", False)
    assert results[1][:2] == ("accept all", True)
