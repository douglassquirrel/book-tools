"""The registry of permanent note IDs, and the matching of a save's notes to it."""


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
    # First, the notes whose text and sentence are both exactly as recorded. Identical
    # notes in identical sentences are paired in order.
    for index, note in enumerate(notes):
        for entry in free:
            if (entry.kind, entry.text, entry.sentence) == (note.kind, note.text, note.sentence):
                pairs[index] = entry
                free.remove(entry)
                break
    for index, note in enumerate(notes):
        if index in pairs:
            matching.carried.append((note, pairs[index]))
        else:
            matching.new.append(note)
    matching.retired = free
    return matching
