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


def changed(index, text=None, sentence=None, base=TEXTS):
    pairs = list(base)
    pairs[index] = (text or pairs[index][0], sentence or pairs[index][1])
    return pairs


def test_a_note_whose_text_changed_but_whose_sentence_did_not_is_carried():
    edited = changed(2, text="See the harbour master’s own account of the great storm of 1881.")
    assert outcome(match(notes(edited), entries(TEXTS))) == {
        "carried": [
            ("endnote:1", "N-0001"), ("endnote:2", "N-0002"),
            ("endnote:3", "N-0003"), ("endnote:4", "N-0004"),
        ],
        "new": [], "retired": [], "unclear": [],
    }


def test_a_note_whose_sentence_changed_but_whose_text_did_not_is_carried():
    edited = changed(1, sentence="The log for March 1881 is missing.")
    assert outcome(match(notes(edited), entries(TEXTS)))["carried"][1] == ("endnote:2", "N-0002")
    assert outcome(match(notes(edited), entries(TEXTS)))["unclear"] == []


def test_a_note_rewritten_and_moved_is_never_guessed():
    edited = changed(
        2,
        text="See the account of the storm given by the harbour master.",
        sentence="That week no ship put out at all.",
    )
    assert outcome(match(notes(edited), entries(TEXTS))) == {
        "carried": [("endnote:1", "N-0001"), ("endnote:2", "N-0002"), ("endnote:4", "N-0004")],
        "new": [],
        "retired": [],
        "unclear": [("endnote:3", ["N-0003"])],
    }


def test_a_note_replaced_by_an_unrelated_one_is_new_and_the_old_one_retired():
    edited = changed(
        2, text="Quite another matter: the price of lamp oil.", sentence="Oil cost four shillings."
    )
    assert outcome(match(notes(edited), entries(TEXTS))) == {
        "carried": [("endnote:1", "N-0001"), ("endnote:2", "N-0002"), ("endnote:4", "N-0004")],
        "new": ["endnote:3"],
        "retired": ["N-0003"],
        "unclear": [],
    }


def test_a_note_rewritten_out_of_recognition_in_the_same_place_is_asked_about():
    edited = changed(2, text="Quite another matter: the price of lamp oil.")
    assert outcome(match(notes(edited), entries(TEXTS)))["unclear"] == [("endnote:3", ["N-0003"])]


def test_one_identical_note_deleted_and_another_added_elsewhere_is_asked_about():
    # An "Ibid." vanished from one sentence and an "Ibid." appeared in another:
    # moved, or one deleted and one written? Not for the kit to guess.
    edited = TEXTS[:3] + [("Ibid.", "The oil ran short in the winter.")]
    assert outcome(match(notes(edited), entries(TEXTS))) == {
        "carried": [("endnote:1", "N-0001"), ("endnote:2", "N-0002"), ("endnote:3", "N-0003")],
        "new": [],
        "retired": [],
        "unclear": [("endnote:4", ["N-0004"])],
    }


def test_a_changed_sentence_is_carried_when_another_identical_note_is_no_close_rival():
    # Both "Ibid." sentences were touched; each is still far more like its old self.
    edited = changed(1, sentence="The log for March 1881 is missing.")
    edited = changed(3, sentence="The keeper kept his own careful tally.", base=edited)
    assert outcome(match(notes(edited), entries(TEXTS)))["carried"] == [
        ("endnote:1", "N-0001"), ("endnote:2", "N-0002"),
        ("endnote:3", "N-0003"), ("endnote:4", "N-0004"),
    ]


def test_two_close_rivals_for_one_entry_are_both_asked_about():
    # One "Ibid." became two in sentences that both resemble the old one.
    edited = TEXTS[:1] + [
        ("Ibid.", "The log for March is missing, alas."),
        ("Ibid.", "The log for March is still missing."),
    ] + TEXTS[2:]
    result = outcome(match(notes(edited), entries(TEXTS)))
    assert result["unclear"] == [("endnote:2", ["N-0002"]), ("endnote:3", ["N-0002"])]
    assert result["new"] == [] and result["retired"] == []
