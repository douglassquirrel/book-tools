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
