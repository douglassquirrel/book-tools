"""The registry of permanent note IDs, and the matching of a save's notes to it."""

import json

from booktools.text import likeness

NAME = "book-tools notes"
VERSION = 1
FIELDS = ("id", "kind", "label", "text", "sentence", "first_seen", "last_seen", "retired_in")
# Found by experiment on invented saves (word-by-word likeness, 0 to 1): a light edit
# scores 0.8 to 0.9, a page number changed in a short citation 0.5, a rewording 0.55 to
# 0.6, another book by the same author 0.45, unrelated text 0 to 0.25.
RECOGNISABLE = 0.5  # the changed text or sentence must be at least this like its old self
RELATED = 0.4  # with neither unchanged, a pair this alike in either is asked about
MARGIN = 0.3  # another candidate within this of the best is a close rival


class Entry:
    """One note the registry knows, alive or retired."""

    def __init__(self, id, kind, text, sentence, label="", first_seen="", last_seen="",
                 retired_in=None):
        self.id = id
        self.kind = kind
        self.text = text
        self.sentence = sentence
        self.label = label
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.retired_in = retired_in


class AssignError(Exception):
    """An --assign names a note or an ID that is not there."""


class Matching:
    """What became of each note of a save and each live entry of the registry."""

    def __init__(self):
        self.carried = []  # (note, entry): the note keeps this entry's ID
        self.new = []  # notes the registry has never seen
        self.retired = []  # live entries with no note any more
        self.unclear = []  # (note, [entries it might be]): to be settled by the user


def match(notes, entries, assign=None):
    """Match the notes of a save to the live entries of the registry.

    `assign` settles what would otherwise be unclear: {note place: entry id or "new"}.
    """
    matching = Matching()
    pairs = {}  # index of the note -> the entry it keeps
    free = list(entries)  # live entries not yet claimed by a note
    declared_new = set()  # indexes of notes the user has said are new
    taken = {}  # entry id -> the place the user assigned it to
    for place, wanted in (assign or {}).items():
        kind = place.partition(":")[0]
        index = next((i for i, note in enumerate(notes) if note.place == place), None)
        if index is None:
            count = sum(1 for note in notes if note.kind == kind)
            has = f"{count or 'no'} {kind}{'' if count == 1 else 's'}"
            raise AssignError(f"there is no {place} in this save (it has {has})")
        if wanted == "new":
            declared_new.add(index)
            continue
        if wanted in taken:
            raise AssignError(f"{wanted} is assigned to both {taken[wanted]} and {place}")
        entry = next((entry for entry in free if entry.id == wanted), None)
        if entry is None:
            raise AssignError(f"{wanted} is not a live ID in the registry")
        if entry.kind != kind:
            raise AssignError(f"{wanted} is an {entry.kind}, so it cannot be {place}")
        taken[wanted] = place
        pairs[index] = entry
        free.remove(entry)
    # First, the notes whose text and sentence are both exactly as recorded. Identical
    # notes in identical sentences are paired in order.
    for index, note in enumerate(notes):
        if index in pairs or index in declared_new:
            continue
        for entry in free:
            if (entry.kind, entry.text, entry.sentence) == (note.kind, note.text, note.sentence):
                pairs[index] = entry
                free.remove(entry)
                break
    # Then the notes of which one of the two is exactly as recorded and the other still
    # recognisably the same, with no close rival. Best first; each carry frees its
    # note and entry from being anyone else's rival.
    open_notes = [
        (i, n) for i, n in enumerate(notes) if i not in pairs and i not in declared_new
    ]
    links = _links(open_notes, free)
    while True:
        clear = [link for link in links if _is_clear(link, links)]
        if not clear:
            break
        best = max(clear, key=lambda link: link.score)
        pairs[best.index] = best.entry
        free.remove(best.entry)
        links = [k for k in links if k.index != best.index and k.entry is not best.entry]
    for index, note in enumerate(notes):
        maybe = sorted((k for k in links if k.index == index), key=lambda k: -k.score)
        if index in pairs:
            matching.carried.append((note, pairs[index]))
        elif maybe:
            matching.unclear.append((note, [k.entry for k in maybe]))
        else:
            matching.new.append(note)
    pending = {link.entry.id for link in links}
    matching.retired = [entry for entry in free if entry.id not in pending]
    return matching


class _Link:
    """A note and an entry that might be the same note."""

    def __init__(self, index, entry, exact, likeness):
        self.index = index  # of the note in the save
        self.entry = entry
        self.exact = exact  # whether the text or the sentence is exactly as recorded
        self.likeness = likeness  # of the other one (or of the more alike, if neither)
        self.score = likeness + 1 if exact else likeness


def _links(numbered_notes, entries):
    links = []
    for index, note in numbered_notes:
        for entry in entries:
            if entry.kind != note.kind:
                continue
            text = likeness(note.text, entry.text)
            sentence = likeness(note.sentence, entry.sentence)
            if note.text == entry.text:
                links.append(_Link(index, entry, True, sentence))
            elif note.sentence == entry.sentence:
                links.append(_Link(index, entry, True, text))
            elif max(text, sentence) >= RELATED:
                links.append(_Link(index, entry, False, max(text, sentence)))
    return links


def _is_clear(link, links):
    """Whether `link` can be carried without asking: one of the two exactly unchanged,
    the other recognisably the same, and no other link of its note or its entry
    nearly as good."""
    if not link.exact or link.likeness < RECOGNISABLE:
        return False
    rivals = (
        k for k in links if k is not link and (k.index == link.index or k.entry is link.entry)
    )
    return all(rival.score <= link.score - MARGIN for rival in rivals)


class RegistryError(Exception):
    """The registry file cannot be used."""


class Registry:
    def __init__(self, entries=(), next=1):
        self.entries = list(entries)  # live entries in document order, then retired ones
        self.next = next  # the number the next new ID will take

    def live(self):
        return [entry for entry in self.entries if entry.retired_in is None]


def load_registry(text):
    """The Registry in a registry file's text; raises RegistryError if it is not one."""
    not_one = RegistryError("it is not a note registry written by note-map")
    try:
        data = json.loads(text)
        if data["registry"] != NAME:
            raise not_one
        version, next, notes = data["version"], data["next"], data["notes"]
        if version > VERSION:
            raise RegistryError(
                f"it was written by a later version of note-map (version {version})"
            )
        entries = [Entry(**{field: note[field] for field in FIELDS}) for note in notes]
    except (ValueError, TypeError, KeyError):
        raise not_one from None
    if not isinstance(next, int) or not all(isinstance(e.id, str) for e in entries):
        raise not_one
    return Registry(entries, next)


def dump_registry(registry):
    """The text of a registry file."""
    data = {
        "registry": NAME,
        "version": VERSION,
        "next": registry.next,
        "notes": [{field: getattr(entry, field) for field in FIELDS} for entry in registry.entries],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def update(registry, matching, save):
    """Return (the Registry after a save, {note place: its ID}).

    `matching` must have nothing unclear. `save` identifies the save (its SHA-256).
    Carried entries take the note's present text and sentence; new notes take the next
    IDs in document order; entries with no note are retired, never deleted, and an ID
    is never used again.
    """
    kept = {id(note): entry for note, entry in matching.carried}
    notes = [note for note, _ in matching.carried] + list(matching.new)
    notes.sort(key=lambda note: (note.kind != "endnote", note.number))
    next = registry.next
    live = []
    ids = {}
    for note in notes:
        old = kept.get(id(note))
        if old is None:
            entry = Entry(f"N-{next:04d}", note.kind, note.text, note.sentence, "", save, save)
            next += 1
        else:
            entry = Entry(
                old.id, old.kind, note.text, note.sentence, old.label, old.first_seen, save
            )
        live.append(entry)
        ids[note.place] = entry.id
    gone = {entry.id for entry in matching.retired}
    retired = []
    for entry in registry.entries:
        if entry.retired_in is not None or entry.id in gone:
            retired.append(
                Entry(
                    entry.id, entry.kind, entry.text, entry.sentence, entry.label,
                    entry.first_seen, entry.last_seen, entry.retired_in or save,
                )
            )
    return Registry(live + retired, next), ids


def where_now(wanted, notes, entries):
    """Where the note of each permanent ID in `wanted` stands in a save, without
    guessing: {ID: (kind, number)}, or {ID: why it cannot be said}.

    `notes` are the save's notes and `entries` every entry of the registry, retired
    ones included. The matching is note-map's, and nothing is recorded.
    """
    matching = match(notes, [entry for entry in entries if entry.retired_in is None])
    placed = {entry.id: (note.kind, note.number) for note, entry in matching.carried}
    maybe = {}
    for note, candidates in matching.unclear:
        for entry in candidates:
            maybe.setdefault(entry.id, []).append(note.place)
    known = {entry.id: entry for entry in entries}
    now = {}
    for id in wanted:
        if id in placed:
            now[id] = placed[id]
        elif id not in known:
            now[id] = f"{id} is not in the registry"
        elif known[id].retired_in is not None:
            now[id] = f"{id} is retired: its note was already gone from an earlier save"
        elif id in maybe:
            now[id] = (
                f"{id} cannot be placed in this save without guessing (it may be"
                f" {' or '.join(maybe[id])}); run note-map on this save to settle it"
            )
        else:
            now[id] = f"the note {id} is not in this save"
    return now
