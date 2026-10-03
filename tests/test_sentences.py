import pytest

from booktools.sentences import sentence_at

pytestmark = pytest.mark.tier1

TEXT = "The lamp was lit. She wrote it down, in ink. “Why?” he asked. No reply"


def at(marker):
    """The sentence for a marker placed where `marker` ends in TEXT."""
    return sentence_at(TEXT, TEXT.index(marker) + len(marker))


def test_a_marker_after_a_full_stop_belongs_to_the_sentence_just_ended():
    assert at("lit.") == "The lamp was lit."
    assert at("in ink.") == "She wrote it down, in ink."


def test_a_marker_in_mid_sentence_belongs_to_the_sentence_around_it():
    assert at("it down,") == "She wrote it down, in ink."
    assert at("The lamp") == "The lamp was lit."


def test_a_question_inside_a_quotation_that_runs_on_in_lower_case_does_not_end_the_sentence():
    assert at("“Why?”") == (
        "“Why?” he asked."
    )
    assert at("he asked.") == "“Why?” he asked."
    quoted = "He said “No.” Then he left."
    assert sentence_at(quoted, 13) == "He said “No.”"


def test_a_paragraph_without_a_final_stop_and_the_ends_of_the_text():
    assert at("No reply") == "No reply"
    assert sentence_at(TEXT, 0) == "The lamp was lit."
    assert sentence_at("", 0) == ""
    assert sentence_at("Title", 5) == "Title"


def test_an_abbreviation_s_stop_inside_a_sentence_is_not_taken_for_its_end():
    text = "See e.g. the 3.5 pints, pp. 4–5, of Dr. Smith. Next one."
    assert sentence_at(text, text.index(", of")) == "See e.g. the 3.5 pints, pp. 4–5, of Dr. Smith."
