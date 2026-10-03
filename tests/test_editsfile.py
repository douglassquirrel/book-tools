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
