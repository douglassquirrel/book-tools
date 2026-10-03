"""Compares two saves of a manuscript paragraph by paragraph."""

import difflib

from booktools.text import likeness

# Found by experiment on invented saves (word-by-word likeness): a paragraph with a word
# or two changed scores about 0.9, one half rewritten about 0.5, unrelated ones under 0.25.
PAIRED = 0.5  # an old and a new paragraph at least this alike are the same one, edited
LARGEST_GAP = 10000  # old x new paragraphs between identical runs, beyond which
# every possible pairing is no longer weighed


def pair(old, new):
    """Pair the paragraphs of two saves by their text.

    `old` and `new` are the paragraph texts in order. Returns (i, j) pairs in reading
    order: both set for a paragraph present in both saves (identical, or alike enough
    to be the same paragraph edited), (i, None) for one only in the old save and
    (None, j) for one only in the new.
    """
    pairs = []
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            pairs.extend(zip(range(i1, i2), range(j1, j2)))
        else:
            pairs.extend(_gap(old, new, i1, i2, j1, j2))
    return pairs


def _gap(old, new, i1, i2, j1, j2):
    """Pair what lies between two runs of identical paragraphs: each old paragraph
    with the new one it is most like, in order, if they are alike enough."""
    rows, columns = i2 - i1, j2 - j1
    if rows * columns > LARGEST_GAP:
        # Too many to weigh every pairing: take them side by side.
        alike = {
            (i, j): likeness(old[i], new[j])
            for i, j in zip(range(i1, i2), range(j1, j2))
        }
    else:
        alike = {
            (i, j): likeness(old[i], new[j]) for i in range(i1, i2) for j in range(j1, j2)
        }
    # best[i][j]: the greatest total likeness of pairs to be had from old[i:], new[j:]
    best = [[0.0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(rows - 1, -1, -1):
        for j in range(columns - 1, -1, -1):
            score = alike.get((i1 + i, j1 + j), 0)
            together = score + best[i + 1][j + 1] if score >= PAIRED else 0
            best[i][j] = max(together, best[i + 1][j], best[i][j + 1])
    pairs = []
    i = j = 0
    while i < rows or j < columns:
        score = alike.get((i1 + i, j1 + j), 0) if i < rows and j < columns else 0
        if score >= PAIRED and best[i][j] == score + best[i + 1][j + 1]:
            pairs.append((i1 + i, j1 + j))
            i, j = i + 1, j + 1
        elif i < rows and (j == columns or best[i][j] == best[i + 1][j]):
            pairs.append((i1 + i, None))
            i += 1
        else:
            pairs.append((None, j1 + j))
            j += 1
    return pairs


def differences(label, old, new, ignore_fonts=()):
    """The report lines for one pair of paragraphs, each a (properties, characters)
    pair as `formats.paragraphs` gives; and how many differences they count as.

    `label` is the paragraph's index as it is to be shown.
    """
    (old_properties, old_chars), (new_properties, new_chars) = old, new
    old_text = "".join(char for char, _ in old_chars)
    new_text = "".join(char for char, _ in new_chars)
    lines = []
    count = 0
    if old_properties != new_properties:
        count += 1
        lines.append(
            f"PARA-PROPS {label}: {old_text[:50]!r}\n"
            f"   old {old_properties[:300]}\n   new {new_properties[:300]}"
        )
    if old_text != new_text:
        count += 1
        matcher = difflib.SequenceMatcher(None, old_text, new_text)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                before = old_text[max(0, i1 - 25) : i2 + 25]
                after = new_text[max(0, j1 - 25) : j2 + 25]
                lines.append(f"TEXT {label}: {tag} {before!r} -> {after!r}")
    elif old_chars != new_chars:
        count += 1
        # Same text, different formatting: say how much and show the first place.
        changed = [
            (at, was, now)
            for at, ((_, was), (_, now)) in enumerate(zip(old_chars, new_chars))
            if was != now
        ]
        beyond_fonts = [
            item
            for item in changed
            if _without(item[1], ignore_fonts) != _without(item[2], ignore_fonts)
        ]
        kind = "FORMAT" if beyond_fonts else "FONT-NAME-ONLY"
        at, was, now = (beyond_fonts or changed)[0]
        around = old_text[max(0, at - 20) : at + 20]
        lines.append(
            f"{kind} {label}: {len(changed)} chars, e.g. at {around!r}: old[{was}] new[{now}]"
        )
    return lines, count


def _without(signature, fonts):
    """A formatting signature with the font names in `fonts` left out."""
    ignored = {f"font={font}" for font in fonts}
    return ",".join(part for part in signature.split(",") if part not in ignored)
