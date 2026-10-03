import pytest

from booktools.trim import common_ends

pytestmark = pytest.mark.tier1


def changed(old, new):
    prefix, suffix = common_ends(old, new)
    return old[prefix : len(old) - suffix], new[prefix : len(new) - suffix]


def test_leaves_the_unchanged_words_at_both_ends_unmarked():
    assert changed(
        "the chat window isn’t where the value is",
        "the chat window is not where the value is",
    ) == ("isn’t", "is not")


def test_marks_a_whole_word_when_letters_inside_it_change():
    assert changed("the colour red", "the color red") == ("colour", "color")


def test_an_added_word_is_a_pure_insertion_and_a_dropped_one_a_pure_deletion():
    assert changed("the cat", "the big cat") == ("", "big ")
    assert changed("the big cat", "the cat") == ("big ", "")
    assert changed("a a a", "a a") == (" a", "")


def test_punctuation_changes_alone():
    assert changed("Stop.", "Stop!") == (".", "!")
    assert changed("1,000 men", "1.000 men") == (",", ".")


def test_nothing_in_common_marks_everything():
    assert changed("abc", "xyz") == ("abc", "xyz")


def test_never_parts_a_letter_from_its_accent():
    assert changed("cafés here", "cafes here") == ("cafés", "cafes")
