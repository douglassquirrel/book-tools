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


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
HEAD = f'<?xml version="1.0"?>\r\n<w:document {W} {W16DU}><w:body>'
NOTES = f"<w:endnotes {W}>"
UNTOUCHED = p("untouched &amp; unchanged") + '<w:p><w:r><w:endnoteReference w:id="1"/></w:r></w:p>'
TAIL = "<w:sectPr/></w:body></w:document>"
PARTS = {
    BODY: HEAD + p("the quick brown fox") + UNTOUCHED + TAIL,
    ENDNOTES: NOTES + '<w:endnote w:id="1">' + p("a note") + "</w:endnote></w:endnotes>",
    "word/styles.xml": f"<w:styles {W}/>",
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
        NOTES + '<w:endnote w:id="1"><w:p>'
        f'<w:del w:id="5"{LOCAL}><w:r><w:delText>a</w:delText></w:r></w:del>'
        f'<w:ins w:id="6"{LOCAL}><w:r><w:t>the</w:t></w:r></w:ins>'
        '<w:r><w:t xml:space="preserve"> note</w:t></w:r></w:p></w:endnote></w:endnotes>'
    )
    assert out["word/styles.xml"] == f"<w:styles {W}/>"
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


def test_accept_all_fails_when_an_inserted_word_is_not_the_one_asked_for():
    results = checked((BODY, "<w:t>slow</w:t>", "<w:t>sluggish</w:t>"))
    assert results[0][:2] == ("reject all", True)
    assert results[1] == (
        "accept all",
        False,
        "paragraph 1 of word/document.xml reads 'the sluggish brown dog'"
        " but the edits ask for 'the slow brown dog'",
    )


def test_accept_all_fails_when_an_edit_was_not_made_at_all():
    spoil = (ENDNOTES, f'<w:ins w:id="6"{LOCAL}><w:r><w:t>the</w:t></w:r></w:ins>', "")
    assert checked(spoil)[1] == (
        "accept all",
        False,
        "paragraph 1 of word/endnotes.xml reads ' note' but the edits ask for 'the note'",
    )


def test_revisions_fails_when_one_carries_another_author_or_date():
    results = checked((BODY, f'<w:ins w:id="2"{BOTH}>', '<w:ins w:id="2" w:author="Eve" w:date="2026-10-03T14:46:00Z">'))
    assert results[2] == (
        "revisions",
        False,
        "revision 2 in word/document.xml does not carry the author and date of this run",
    )
    other_date = BOTH.replace("14:46", "14:47")
    assert failed(checked((BODY, f'<w:del w:id="3"{BOTH}>', f'<w:del w:id="3"{other_date}>'))) == [
        "revisions"
    ]


def test_revisions_fails_when_an_edit_does_not_have_exactly_its_own_pair():
    missing = checked((ENDNOTES, f'<w:ins w:id="6"{LOCAL}><w:r><w:t>the</w:t></w:r></w:ins>', ""))
    assert missing[2] == ("revisions", False, "revision 6 (w:ins) is missing from the copy")
    extra = f'<w:ins w:id="9"{BOTH}><w:r><w:t>!</w:t></w:r></w:ins>'
    added = checked((BODY, "<w:sectPr/>", "<w:p>" + extra + "</w:p><w:sectPr/>"))
    assert added[2] == (
        "revisions",
        False,
        "the copy holds 7 tracked changes more than the original; the edits account for 6",
    )
    twice = f'<w:ins w:id="2"{BOTH}><w:r><w:t>slow</w:t></w:r></w:ins>'
    doubled = checked((BODY, twice, twice + twice))
    assert doubled[2] == ("revisions", False, "revision 2 appears 2 times in the copy")


def test_package_fails_when_an_untouched_paragraph_or_part_is_not_byte_identical():
    # The text is the same, so the first two checks pass; only the bytes differ.
    results = checked((BODY, "<w:p><w:r><w:t>untouched", '<w:p w:rsidR="00FF"><w:r><w:t>untouched'))
    assert failed(results) == ["package"]
    assert results[3][2] == "paragraph 2 of word/document.xml was not edited but its XML has changed"
    results = checked((BODY, "<w:sectPr/>", "<w:sectPr></w:sectPr>"))
    assert results[3] == (
        "package",
        False,
        "word/document.xml has changed outside its paragraphs",
    )
    results = checked(("word/styles.xml", "/>", "></w:styles>"))
    assert results[3] == ("package", False, "word/styles.xml has changed and no edit is in it")


def test_package_fails_when_an_edited_part_is_no_longer_well_formed():
    results = checked((ENDNOTES, "</w:endnote></w:endnotes>", "</w:endnotes>"))
    assert results[3][:2] == ("package", False)
    assert results[3][2].startswith("word/endnotes.xml is not well-formed XML: ")


def test_new_ids_start_above_the_highest_id_anywhere_in_the_document():
    from booktools.propose import highest_id

    parts = {
        BODY: '<w:document><w:bookmarkStart w:id="12" w:name="a"/><w:ins w:id="40" w:author="E"/>'
        '<w:p w14:paraId="7FFFFFFF"/></w:document>',
        ENDNOTES: '<w:endnotes><w:endnote w:type="separator" w:id="-1"/><w:endnote w:id="7"/></w:endnotes>',
        "word/comments.xml": '<w:comments><w:comment w:id="55"/></w:comments>',
        "word/styles.xml": "<w:styles/>",
    }
    assert highest_id(parts) == 55
    assert highest_id({BODY: "<w:document/>"}) == 0
