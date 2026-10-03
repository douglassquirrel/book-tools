import pytest

from booktools.compare import pair

pytestmark = pytest.mark.tier1

A = "The lamp was lit at dusk, and the keeper is not one to waste oil."
B = "She wrote every figure in a large ledger."
C = "The log for March is missing."
B_EDITED = "She wrote every single figure in a large ledger."
X = "A paragraph added in the later save, about nothing above."


def test_identical_saves_pair_every_paragraph_with_itself():
    assert pair([A, B, C], [A, B, C]) == [(0, 0), (1, 1), (2, 2)]
    assert pair([], []) == []


def test_a_paragraph_added_does_not_put_the_later_ones_out_of_step():
    assert pair([A, B, C], [A, X, B, C]) == [(0, 0), (None, 1), (1, 2), (2, 3)]
    assert pair([A, B, C], [X, A, B, C]) == [(None, 0), (0, 1), (1, 2), (2, 3)]
    assert pair([], [A]) == [(None, 0)]


def test_a_paragraph_removed_is_reported_where_it_stood():
    assert pair([A, B, C], [A, C]) == [(0, 0), (1, None), (2, 1)]
    assert pair([A], []) == [(0, None)]


def test_an_edited_paragraph_is_paired_with_its_old_self():
    assert pair([A, B, C], [A, B_EDITED, C]) == [(0, 0), (1, 1), (2, 2)]


def test_an_edited_paragraph_beside_an_added_one_still_finds_its_old_self():
    assert pair([A, B, C], [A, X, B_EDITED, C]) == [(0, 0), (None, 1), (1, 2), (2, 3)]
    assert pair([A, B, C], [A, B_EDITED, X, C]) == [(0, 0), (1, 1), (None, 2), (2, 3)]


def test_a_paragraph_replaced_by_an_unrelated_one_is_removed_and_added():
    assert pair([A, B, C], [A, X, C]) == [(0, 0), (1, None), (None, 1), (2, 2)]


def test_identical_paragraphs_are_paired_in_order():
    assert pair(["", A, "", ""], ["", A, ""]) == [(0, 0), (1, 1), (2, 2), (3, None)]


def para(text, formatting="", properties=""):
    return (properties, [(char, formatting) for char in text])


def lines(old, new, **more):
    from booktools.compare import differences

    return differences("7", old, new, **more)


LONG = "At the start of a long paragraph, the chat window isn’t where the value is, and so on."


def test_paragraphs_that_are_the_same_give_no_lines():
    assert lines(para("Same.", "b"), para("Same.", "b")) == ([], 0)


def test_a_text_change_shows_each_differing_span_with_25_characters_either_side():
    # The spans are those Python's sequence matcher finds, letter by letter.
    new = LONG.replace("isn’t", "is not").replace("At the", "At  the")
    assert lines(para(LONG), para(new)) == (
        [
            "TEXT 7: insert 'At the start of a long para' -> 'At  the start of a long para'",
            "TEXT 7: insert 'graph, the chat window isn’t where the value is, a'"
            " -> 'graph, the chat window is not where the value is, a'",
            "TEXT 7: replace 'raph, the chat window isn’t where the value is, and'"
            " -> 'aph, the chat window is not where the value is, and'",
        ],
        1,
    )


def test_a_change_of_paragraph_properties_shows_both():
    old = para("Centred text that runs on for more than fifty characters in all.", properties="<w:pPr><w:jc w:val=\"center\"/></w:pPr>")
    new = para("Centred text that runs on for more than fifty characters in all.")
    assert lines(old, new) == (
        [
            "PARA-PROPS 7: 'Centred text that runs on for more than fifty char'\n"
            '   old <w:pPr><w:jc w:val="center"/></w:pPr>\n'
            "   new ",
        ],
        1,
    )


def test_the_same_text_in_different_formatting_says_how_many_characters_and_shows_the_first():
    old = ("", [(c, "") for c in "She wrote every figure in a "] + [(c, "b") for c in "large"] + [(c, "") for c in " ledger."])
    new = para("She wrote every figure in a large ledger.")
    assert lines(old, new) == (
        ["FORMAT 7: 5 chars, e.g. at 'e every figure in a large ledger.': old[b] new[]"],
        1,
    )


def test_a_font_name_listed_to_be_ignored_is_reported_apart_and_only_then():
    old = para("A caption.", "i,font=Times-Roman")
    new = para("A caption.", "i")
    assert lines(old, new) == (
        ["FORMAT 7: 10 chars, e.g. at 'A caption.': old[i,font=Times-Roman] new[i]"],
        1,
    )
    assert lines(old, new, ignore_fonts=["Arial", "Times-Roman"]) == (
        ["FONT-NAME-ONLY 7: 10 chars, e.g. at 'A caption.': old[i,font=Times-Roman] new[i]"],
        1,
    )
    # With another difference as well, it is a formatting change, and the example
    # shown is a character that differs in more than the font name.
    mixed = ("", [("A", "i,font=Times-Roman")] + [(c, "b,font=Times-Roman") for c in " caption."])
    assert lines(mixed, new, ignore_fonts=["Times-Roman"]) == (
        ["FORMAT 7: 10 chars, e.g. at 'A caption.': old[b,font=Times-Roman] new[i]"],
        1,
    )


def test_properties_and_text_both_changed_count_as_two():
    old = para("One.", properties="<w:pPr><w:keepNext/></w:pPr>")
    assert lines(old, para("Two.")) == (
        [
            "PARA-PROPS 7: 'One.'\n   old <w:pPr><w:keepNext/></w:pPr>\n   new ",
            "TEXT 7: replace 'One.' -> 'Two.'",
        ],
        2,
    )


def part(*texts):
    return "<w:body>" + "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in texts) + "</w:body>"


def report(old, new, **more):
    from booktools.compare import compare_part

    return compare_part("word/document.xml", old, new, **more)


def test_a_part_that_is_the_same_has_only_its_header_and_a_count_of_nothing():
    assert report(part(A, B), part(A, B)) == [
        "===== word/document.xml paragraphs 2 2",
        "differing paragraphs 0",
    ]


def test_added_and_removed_paragraphs_are_named_and_later_ones_compared_in_step():
    old = part(A, B, C, "Gone for good, this one, and unlike the rest.")
    new = part(A, X, B_EDITED, C)
    assert report(old, new) == [
        "===== word/document.xml paragraphs 4 4",
        "ADDED 1: 'A paragraph added in the later save, about nothing above.'",
        "TEXT 2 (old 1): insert 'She wrote every figure in a large ledger'"
        " -> 'She wrote every single figure in a large ledger'",
        "REMOVED 3: 'Gone for good, this one, and unlike the rest.'",
        "differing paragraphs 3",
    ]


def test_a_long_added_paragraph_is_shown_by_its_first_60_characters():
    long = "0123456789" * 7
    assert report(part(A), part(A, long))[1] == f"ADDED 1: '{long[:60]}'"


def test_a_part_one_save_lacks_is_all_added_or_all_removed():
    assert report("", part(A)) == [
        "===== word/document.xml paragraphs 0 1",
        f"ADDED 0: '{A[:60]}'",
        "differing paragraphs 1",
    ]
    assert report(part(A), "")[1] == f"REMOVED 0: '{A[:60]}'"


def test_the_fonts_to_ignore_reach_the_comparison_of_each_pair():
    old = '<w:p><w:r><w:rPr><w:rFonts w:ascii="Times-Roman"/></w:rPr><w:t>Cap.</w:t></w:r></w:p>'
    new = "<w:p><w:r><w:t>Cap.</w:t></w:r></w:p>"
    assert report(old, new, ignore_fonts=["Times-Roman"])[1].startswith("FONT-NAME-ONLY 0: 4 chars")
    assert report(old, new)[1].startswith("FORMAT 0: 4 chars")


def test_a_very_large_gap_is_paired_side_by_side(monkeypatch):
    import booktools.compare as compare

    monkeypatch.setattr(compare, "LARGEST_GAP", 1)  # so that two by two counts as large
    # Side by side: the first old with the first new (unlike: removed and added), the
    # second with the second (alike: one paragraph, edited).
    assert pair([A, B], [X, B_EDITED]) == [(0, None), (None, 0), (1, 1)]
    # Whereas with every pairing weighed, an edited paragraph is found out of step.
    monkeypatch.setattr(compare, "LARGEST_GAP", 10000)
    assert pair([A, B], [B_EDITED, X]) == [(0, None), (1, 0), (None, 1)]
    monkeypatch.setattr(compare, "LARGEST_GAP", 1)
    assert pair([A, B], [B_EDITED, X]) == [(0, None), (1, None), (None, 0), (None, 1)]
