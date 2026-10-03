"""The registry of permanent note IDs, and the matching of a save's notes to it."""

import difflib
import re

WORD = re.compile(r"\w+")
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
    # Then the notes of which one of the two is exactly as recorded and the other still
    # recognisably the same, with no close rival. Best first; each carry frees its
    # note and entry from being anyone else's rival.
    links = _links([(i, n) for i, n in enumerate(notes) if i not in pairs], free)
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
    pending = {id(k.entry) for k in links}
    matching.retired = [entry for entry in free if id(entry) not in pending]
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


def likeness(one, other):
    """How alike two pieces of text are, from 0 to 1, comparing them word by word."""
    a, b = WORD.findall(one.lower()), WORD.findall(other.lower())
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
