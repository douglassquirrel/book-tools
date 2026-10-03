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


MOVED = changed(
    2,
    text="See the account of the storm given by the harbour master.",
    sentence="That week no ship put out at all.",
)


def test_assign_settles_an_unclear_note_as_an_existing_id_or_as_new():
    kept = match(notes(MOVED), entries(TEXTS), {"endnote:3": "N-0003"})
    assert outcome(kept) == {
        "carried": [
            ("endnote:1", "N-0001"), ("endnote:2", "N-0002"),
            ("endnote:3", "N-0003"), ("endnote:4", "N-0004"),
        ],
        "new": [], "retired": [], "unclear": [],
    }
    fresh = match(notes(MOVED), entries(TEXTS), {"endnote:3": "new"})
    assert outcome(fresh) == {
        "carried": [("endnote:1", "N-0001"), ("endnote:2", "N-0002"), ("endnote:4", "N-0004")],
        "new": ["endnote:3"], "retired": ["N-0003"], "unclear": [],
    }


def test_an_assignment_that_makes_no_sense_is_refused():
    from booktools.registry import AssignError

    cases = {
        ("endnote:9", "N-0003"): "there is no endnote:9 in this save (it has 4 endnotes)",
        ("endnote:3", "N-0099"): "N-0099 is not a live ID in the registry",
        ("footnote:1", "N-0003"): "there is no footnote:1 in this save (it has no footnotes)",
    }
    for (place, id), message in cases.items():
        with pytest.raises(AssignError) as caught:
            match(notes(MOVED), entries(TEXTS), {place: id})
        assert str(caught.value) == message
    with pytest.raises(AssignError) as caught:
        match(notes(MOVED), entries(TEXTS), {"endnote:3": "N-0003", "endnote:4": "N-0003"})
    assert str(caught.value) == "N-0003 is assigned to both endnote:3 and endnote:4"
    mixed = notes(MOVED) + notes([("A footnote.", "Some sentence.")], "footnote")
    with pytest.raises(AssignError) as caught:
        match(mixed, entries(TEXTS), {"footnote:1": "N-0003"})
    assert str(caught.value) == "N-0003 is an endnote, so it cannot be footnote:1"


def after(pairs, registry=None, save="save-1", assign=None):
    from booktools.registry import Registry, update

    registry = registry or Registry()
    matching = match(notes(pairs), registry.live(), assign)
    return update(registry, matching, save)


def summary(registry):
    return [
        (e.id, e.text[:12], e.first_seen, e.last_seen, e.retired_in) for e in registry.entries
    ]


def test_a_first_run_numbers_every_note_in_document_order():
    registry, ids = after(TEXTS)
    assert ids == {"endnote:1": "N-0001", "endnote:2": "N-0002", "endnote:3": "N-0003", "endnote:4": "N-0004"}
    assert registry.next == 5
    assert summary(registry)[0] == ("N-0001", "Recorded by ", "save-1", "save-1", None)
    assert [e.id for e in registry.entries] == ["N-0001", "N-0002", "N-0003", "N-0004"]


def test_ids_are_carried_while_numbers_move_and_a_retired_id_is_never_used_again():
    first, _ = after(TEXTS)
    added = TEXTS[:1] + [("A wholly new remark about tides.", "The tide tables were wrong.")] + TEXTS[1:]
    second, ids = after(added, first, "save-2")
    assert ids == {
        "endnote:1": "N-0001", "endnote:2": "N-0005", "endnote:3": "N-0002",
        "endnote:4": "N-0003", "endnote:5": "N-0004",
    }
    assert summary(second)[1] == ("N-0005", "A wholly new", "save-2", "save-2", None)
    # Now delete that note and add another: the new one must not take N-0005.
    third, ids = after(TEXTS + [("Yet another.", "A last sentence.")], second, "save-3")
    assert ids["endnote:5"] == "N-0006"
    assert [(e.id, e.retired_in) for e in third.entries] == [
        ("N-0001", None), ("N-0002", None), ("N-0003", None), ("N-0004", None),
        ("N-0006", None), ("N-0005", "save-3"),
    ]
    assert third.next == 7
    assert [e.last_seen for e in third.entries] == ["save-3"] * 5 + ["save-2"]


def test_a_carried_entry_takes_the_note_s_present_text_and_sentence_and_keeps_its_label():
    first, _ = after(TEXTS)
    first.entries[2].label = "harbour master"
    edited = changed(2, text="See the harbour master’s own account of the great storm of 1881.")
    second, _ = after(edited, first, "save-2")
    entry = second.entries[2]
    assert (entry.id, entry.label, entry.first_seen, entry.last_seen) == (
        "N-0003", "harbour master", "save-1", "save-2",
    )
    assert entry.text.endswith("great storm of 1881.")


def test_the_registry_file_round_trips_and_an_unchanged_save_leaves_it_identical():
    from booktools.registry import dump_registry, load_registry

    first, _ = after(TEXTS + [("Twö “quoted”", "S.")])
    first.entries[0].label = "Trinity House"
    text = dump_registry(first)
    assert text.endswith("\n") and "Twö “quoted”" in text  # readable, not escaped
    loaded = load_registry(text)
    assert dump_registry(loaded) == text
    again, _ = after(TEXTS + [("Twö “quoted”", "S.")], loaded, "save-1")
    assert dump_registry(again) == text


def test_a_damaged_registry_is_refused():
    from booktools.registry import RegistryError, load_registry

    for text in ("", "not json", "[]", '{"notes": []}', '{"registry": "book-tools notes", "version": 1, "next": 2, "notes": [{"id": "N-0001"}]}'):
        with pytest.raises(RegistryError):
            load_registry(text)
    with pytest.raises(RegistryError) as caught:
        load_registry('{"registry": "book-tools notes", "version": 2, "next": 1, "notes": []}')
    assert str(caught.value) == "it was written by a later version of note-map (version 2)"
