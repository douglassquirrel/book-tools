import json

import pytest

from booktools.editsfile import EditsFileError, parse_edits

pytestmark = pytest.mark.tier1


def fields(e):
    return (e.index, e.id, e.where, e.find, e.replace, e.occurrence, e.why, e.name)


def test_reads_every_field_of_an_edit():
    text = json.dumps(
        [
            {
                "id": "D7-14",
                "where": "endnote:42",
                "find": "isn’t",
                "replace": "is not",
                "occurrence": 2,
                "why": "no contractions",
            }
        ]
    )
    (edit,) = parse_edits(text)
    assert fields(edit) == (
        1, "D7-14", ("endnote", 42), "isn’t", "is not", 2, "no contractions", "edit 1 (D7-14)",
    )


def test_only_find_and_replace_are_required_and_where_defaults_to_the_body():
    first, second, third = parse_edits(
        '[{"find": "a", "replace": ""},'
        ' {"find": "b", "replace": "c", "where": "all"},'
        ' {"find": "d", "replace": "e", "where": "footnote:3"}]'
    )
    assert fields(first) == (1, "", ("body",), "a", "", None, "", "edit 1")
    assert (second.where, third.where) == (("all",), ("footnote", 3))


def test_an_empty_list_is_no_edits_and_not_an_error():
    assert parse_edits("[]") == []


def problems(text):
    with pytest.raises(EditsFileError) as caught:
        parse_edits(text)
    return caught.value.problems


def one(**item):
    return json.dumps([item])


def test_a_file_that_is_not_a_json_list_is_refused():
    assert problems("{not json") == [
        "not valid JSON: Expecting property name enclosed in double quotes (line 1, column 2)"
    ]
    assert problems('{"find": "a"}') == ["the edits file must hold a JSON list of edits"]
    assert problems('["a"]') == ['edit 1: must be an object with "find" and "replace"']


def test_find_and_replace_must_be_given_as_text():
    assert problems(one(replace="x")) == ['edit 1: "find" must be text and not empty']
    assert problems(one(find="", replace="x")) == ['edit 1: "find" must be text and not empty']
    assert problems(one(id="A1", find="x")) == [
        'edit 1 (A1): "replace" must be text (empty to delete)'
    ]
    assert problems(one(find="x", replace=3)) == ['edit 1: "replace" must be text (empty to delete)']


def test_a_replace_equal_to_its_find_is_an_error():
    assert problems(one(id="A1", find="same", replace="same")) == [
        'edit 1 (A1): "replace" is the same as "find", so the edit would change nothing'
    ]
    # The same text spelt with composed and decomposed accents is still the same.
    assert problems(one(find="café", replace="café")) == [
        'edit 1: "replace" is the same as "find", so the edit would change nothing'
    ]


def test_where_and_occurrence_must_be_of_the_stated_forms():
    bad_where = 'edit 1: "where" must be body, all, endnote:N or footnote:N (N from 1)'
    for where in ("header", "endnote:", "endnote:0", "endnote:x", "body:2", 7):
        assert problems(one(find="a", replace="b", where=where)) == [bad_where]
    bad_occurrence = 'edit 1: "occurrence" must be a whole number, 1 or more'
    for occurrence in (0, -1, "2", 1.5, True):
        assert problems(one(find="a", replace="b", occurrence=occurrence)) == [bad_occurrence]


def test_text_holding_a_line_break_or_tab_is_refused_as_out_of_scope():
    assert problems(one(find="a\nb", replace="c")) == [
        'edit 1: "find" holds a line break; an edit must stay within one paragraph'
        " (join or split paragraphs by hand in Word)"
    ]
    assert problems(one(find="a", replace="b\nc")) == [
        'edit 1: "replace" holds a line break; an edit must stay within one paragraph'
        " (join or split paragraphs by hand in Word)"
    ]
    assert problems(one(find="a", replace="b\tc")) == [
        'edit 1: "replace" holds a tab, which cannot be proposed as a tracked change here'
    ]


def test_unknown_keys_and_wrong_kinds_are_named_and_every_problem_is_listed():
    text = json.dumps(
        [
            {"find": "a", "replace": "b", "fnd": "typo"},
            {"id": 5, "find": "a", "replace": "b", "why": ["x"]},
            {"find": "ok", "replace": "fine"},
            {"find": "a", "replace": "a"},
        ]
    )
    assert problems(text) == [
        'edit 1: unknown key "fnd"',
        'edit 2: "id" must be text',
        'edit 2: "why" must be text',
        'edit 4: "replace" is the same as "find", so the edit would change nothing',
    ]
