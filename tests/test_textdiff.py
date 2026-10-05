import pytest

from booktools.textdiff import text_diff

pytestmark = pytest.mark.tier1

OLD = """# The Lighthouse Ledger

The lamp was lit at dusk.[^1]

She wrote every figure.[^2]

[^1]: Recorded by Trinity House.

[^2]: Ibid.
"""


def test_the_same_text_has_no_difference():
    assert text_diff(OLD, OLD) == []


RENUMBERED = """# The Lighthouse Ledger

A new opening line.[^1]

The lamp was lit at dusk.[^2]

She wrote every figure.[^3]

[^1]: A new first note.

[^2]: Recorded by Trinity House.

[^3]: Ibid.
"""


def test_renumbering_alone_is_not_a_change():
    # Only the added line and the added note are reported; the two notes that were
    # renumbered are not, and nor are the blank lines that came with the new ones.
    assert text_diff(OLD, RENUMBERED) == [
        "=== BODY insert",
        "  NEW: A new opening line.[^1]",
        "=== NOTES insert old [] new [1]",
        "  NEW: A new first note.",
    ]


def test_a_changed_line_and_a_changed_note_show_old_and_new():
    new = OLD.replace("at dusk", "at dawn").replace("Ibid.", "Ibid., 44.")
    assert text_diff(OLD, new) == [
        "=== BODY replace",
        "  OLD: The lamp was lit at dusk.[^1]",
        "  NEW: The lamp was lit at dawn.[^1]",
        "=== NOTES replace old [2] new [2]",
        "  OLD: Ibid.",
        "  NEW: Ibid., 44.",
    ]


def test_a_removed_line_and_a_removed_note():
    new = OLD.replace("She wrote every figure.[^2]\n\n", "").replace("\n[^2]: Ibid.\n", "")
    assert text_diff(OLD, new) == [
        "=== BODY delete",
        "  OLD: She wrote every figure.[^2]",
        "=== NOTES delete old [2] new []",
        "  OLD: Ibid.",
    ]


LONG = (
    "The keeper climbed the stair each evening with the oil can in one hand and the ledger"
    " in the other, counted the steps aloud as his father had done, trimmed the wick, wiped"
    " the lens with a soft cloth, and wrote down the hour at which the lamp was lit.[^1]"
)
LONG_NOTE = (
    "Recorded by Trinity House in the station log for that year, which the keeper’s daughter"
    " copied out in a fair hand and gave to the county record office, where it was bound with"
    " the tide tables and may still be read on any weekday, p. 14."
)
assert len(LONG) > 200 and len(LONG_NOTE) > 200
BOOK = f"# The Lighthouse Ledger\n\n{LONG}\n\nShe wrote every figure.[^2]\n\n[^1]: {LONG_NOTE}\n\n[^2]: Ibid.\n"


def test_a_small_change_in_a_long_paragraph_or_note_is_shown_as_its_changed_words_only():
    new = BOOK.replace("soft cloth", "clean cloth").replace("p. 14.", "p. 41.")
    assert text_diff(BOOK, new) == [
        "=== BODY replace",
        "  CHANGED: …k, wiped the lens with a [soft → clean] cloth, and wrote down th…",
        "=== NOTES replace old [1] new [1]",
        "  CHANGED: … read on any weekday, p. [14. → 41.]",
    ]


def test_each_change_in_a_long_paragraph_has_a_line_and_words_added_or_cut_show_an_empty_side():
    new = BOOK.replace("soft cloth", "clean cloth").replace("steps aloud as", "steps as")
    new = new.replace("The keeper climbed", "The old keeper climbed")
    assert text_diff(BOOK, new) == [
        "=== BODY replace",
        "  CHANGED: The [→ old ]keeper climbed the stair …",
        "  CHANGED: …other, counted the steps [aloud  →]as his father had done, t…",
        "  CHANGED: …k, wiped the lens with a [soft → clean] cloth, and wrote down th…",
    ]


def test_a_note_renumbered_inside_a_changed_long_paragraph_is_not_shown_as_a_change():
    new = BOOK.replace("soft cloth", "clean cloth").replace("lit.[^1]", "lit.[^7]")
    assert text_diff(BOOK, new) == [
        "=== BODY replace",
        "  CHANGED: …k, wiped the lens with a [soft → clean] cloth, and wrote down th…",
    ]


def test_full_gives_the_whole_lines_for_a_long_paragraph_as_before():
    new = BOOK.replace("soft cloth", "clean cloth")
    assert text_diff(BOOK, new, full=True) == [
        "=== BODY replace",
        f"  OLD: {LONG}",
        f"  NEW: {LONG.replace('soft', 'clean')}",
    ]


def test_a_long_paragraph_rewritten_is_shown_whole_since_its_changed_words_would_be_longer():
    rewritten = " ".join(
        word.upper() if number % 2 else word for number, word in enumerate(LONG.split(" "))
    )
    assert text_diff(BOOK, BOOK.replace(LONG, rewritten)) == [
        "=== BODY replace",
        f"  OLD: {LONG}",
        f"  NEW: {rewritten}",
    ]


def test_lines_added_removed_or_not_one_for_one_print_in_full_however_long():
    other = LONG.replace("keeper", "warden").replace("[^1]", "")
    assert text_diff(BOOK, BOOK.replace(LONG, LONG.replace("soft", "clean") + "\n\n" + other)) == [
        "=== BODY replace",
        f"  OLD: {LONG}",
        f"  NEW: {LONG.replace('soft', 'clean')}",
        f"  NEW: {other}",
    ]


def test_in_a_block_of_several_changed_lines_each_pair_is_shown_in_turn():
    new = BOOK.replace("soft cloth", "clean cloth").replace("every figure", "each figure")
    assert text_diff(BOOK, new) == [
        "=== BODY replace",
        "  CHANGED: …k, wiped the lens with a [soft → clean] cloth, and wrote down th…",
        "  OLD: She wrote every figure.[^2]",
        "  NEW: She wrote each figure.[^2]",
    ]
