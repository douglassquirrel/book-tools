import pytest

from booktools.notes import Note
from booktools.registry import Entry, match

pytestmark = pytest.mark.tier1

TEXTS = [
    ("Recorded by Trinity House in the station log.", "The lamp was lit at dusk."),
    ("Ibid.", "The log for March is missing."),
    ("See the harbour master’s own account of the storm.", "No ship put out that week."),
    ("Ibid.", "The keeper kept his own tally."),
]


def notes(pairs, kind="endnote"):
    return [Note(kind, n, text, sentence, "", n) for n, (text, sentence) in enumerate(pairs, 1)]


def entries(pairs, kind="endnote"):
    return [Entry(f"N-{n:04d}", kind, text, sentence) for n, (text, sentence) in enumerate(pairs, 1)]


def outcome(matching):
    return {
        "carried": [(note.place, entry.id) for note, entry in matching.carried],
        "new": [note.place for note in matching.new],
        "retired": [entry.id for entry in matching.retired],
        "unclear": [(note.place, [e.id for e in maybe]) for note, maybe in matching.unclear],
    }


def test_with_an_empty_registry_every_note_is_new():
    assert outcome(match(notes(TEXTS), [])) == {
        "carried": [],
        "new": ["endnote:1", "endnote:2", "endnote:3", "endnote:4"],
        "retired": [],
        "unclear": [],
    }


def test_an_unchanged_save_carries_every_id():
    assert outcome(match(notes(TEXTS), entries(TEXTS))) == {
        "carried": [
            ("endnote:1", "N-0001"), ("endnote:2", "N-0002"),
            ("endnote:3", "N-0003"), ("endnote:4", "N-0004"),
        ],
        "new": [],
        "retired": [],
        "unclear": [],
    }


def test_a_note_added_in_the_middle_is_new_and_every_other_id_is_carried():
    added = TEXTS[:1] + [("A wholly new remark about tides.", "The tide tables were wrong.")] + TEXTS[1:]
    assert outcome(match(notes(added), entries(TEXTS))) == {
        "carried": [
            ("endnote:1", "N-0001"), ("endnote:3", "N-0002"),
            ("endnote:4", "N-0003"), ("endnote:5", "N-0004"),
        ],
        "new": ["endnote:2"],
        "retired": [],
        "unclear": [],
    }


def test_a_note_deleted_is_retired_and_the_others_keep_their_ids():
    assert outcome(match(notes(TEXTS[:2] + TEXTS[3:]), entries(TEXTS))) == {
        "carried": [("endnote:1", "N-0001"), ("endnote:2", "N-0002"), ("endnote:3", "N-0004")],
        "new": [],
        "retired": ["N-0003"],
        "unclear": [],
    }


def test_two_identical_notes_are_told_apart_by_their_sentences_even_when_they_swap_places():
    swapped = [TEXTS[0], TEXTS[3], TEXTS[2], TEXTS[1]]
    assert outcome(match(notes(swapped), entries(TEXTS)))["carried"] == [
        ("endnote:1", "N-0001"), ("endnote:2", "N-0004"),
        ("endnote:3", "N-0003"), ("endnote:4", "N-0002"),
    ]


def test_endnotes_and_footnotes_are_matched_each_among_their_own_kind():
    same = [("Ibid.", "The log for March is missing.")]
    matching = match(notes(same, "footnote"), entries(same, "endnote"))
    assert outcome(matching) == {
        "carried": [], "new": ["footnote:1"], "retired": ["N-0001"], "unclear": [],
    }
