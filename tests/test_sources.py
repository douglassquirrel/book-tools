import pytest

from booktools.sources import assemble, best_turn, needs_ocr, page_header, score, split_pages

pytestmark = pytest.mark.tier1


def test_pages_are_split_on_form_feeds_and_the_empty_tail_is_dropped():
    assert split_pages("one\n\ftwo\n\f") == ["one\n", "two\n"]
    assert split_pages("only\n\f") == ["only\n"]  # a one-page PDF
    assert split_pages("one\n\f\f") == ["one\n", ""]  # its last page is blank
    # Only the one piece after the last form feed is dropped, as the script did.
    assert split_pages("one\n\f   \n\f") == ["one\n", "   \n"]
    assert split_pages("") == []


def test_a_page_with_fewer_characters_than_the_threshold_goes_to_ocr():
    assert needs_ocr("") is True
    assert needs_ocr("a b  c\n" * 26) is True  # 78 characters that are not spaces
    assert needs_ocr("x" * 79) is True
    assert needs_ocr("x" * 80) is False
    assert needs_ocr("x" * 10, min_chars=10) is False


def test_the_page_header_forms_are_exact():
    assert page_header(3, 12) == "=== PDF page 3 of 12 ==="
    assert page_header(3, 12, ocr=True) == "=== PDF page 3 of 12 (OCR) ==="
    assert page_header(3, 12, ocr=True, turned=90) == (
        "=== PDF page 3 of 12 (OCR, page turned 90° clockwise) ==="
    )


def test_the_text_of_a_pdf_is_each_page_under_its_header():
    assert assemble(["first\n", "second", ""], [False, True, True], [0, 270, 0]) == (
        "\n=== PDF page 1 of 3 ===\nfirst\n"
        "\n=== PDF page 2 of 3 (OCR, page turned 270° clockwise) ===\nsecond"
        "\n=== PDF page 3 of 3 (OCR) ===\n"
    )
    assert assemble([], [], []) == ""


TSV = "\n".join(
    [
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
        "5\t1\t1\t1\t1\t1\t10\t10\t50\t12\t96.5\tlighthouse",
        "5\t1\t1\t1\t1\t2\t70\t10\t50\t12\t80\tlamp",
        "5\t1\t1\t1\t1\t3\t130\t10\t50\t12\t79.9\tledger",  # not confident enough
        "5\t1\t1\t1\t1\t4\t190\t10\t50\t12\t95\toil",  # too short
        "5\t1\t1\t1\t1\t5\t250\t10\t50\t12\t95\t1881,",  # not letters
        "4\t1\t1\t1\t1\t0\t10\t10\t300\t12\t-1\t",  # a line, not a word
        "5\t1\t1\t1\t2\t1\t10\t30\t50\t12\t91\t keeper ",
        "a short row",
    ]
)


def test_the_score_counts_confident_words_of_four_letters_or_more():
    assert score(TSV) == 3
    assert score("") == 0
    assert score(TSV.splitlines()[0]) == 0


def test_a_turn_is_kept_only_when_it_reads_clearly_better():
    assert best_turn({0: 200}) == 0  # reads well as it is: no turn was tried
    assert best_turn({0: 150, 90: 999, 180: 0, 270: 0}) == 0  # 150 is well enough
    assert best_turn({0: 149, 90: 999, 180: 0, 270: 0}) == 90
    assert best_turn({0: 2, 90: 40, 180: 1, 270: 0}) == 90
    assert best_turn({0: 10, 90: 15, 180: 12, 270: 0}) == 0  # 15 is not more than 1.5 times 10
    assert best_turn({0: 10, 90: 16, 180: 0, 270: 0}) == 90
    assert best_turn({0: 1, 90: 3, 180: 0, 270: 0}) == 0  # more than 1.5 times, but not 3 more
    assert best_turn({0: 0, 90: 3, 180: 0, 270: 0}) == 90
    # A later turn must beat the best so far by the same rule, as the script's loop did.
    assert best_turn({0: 2, 90: 10, 180: 14, 270: 16}) == 270
    assert best_turn({0: 2, 90: 10, 180: 14, 270: 15}) == 90
