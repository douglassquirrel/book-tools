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
