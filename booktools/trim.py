"""Works out which part of an edit actually changes."""

from booktools.text import characters, nfc


def difference(old, new):
    """Return (start, end, text): `old[start:end]` is what changes, and `text` is what
    it becomes.

    The words `old` and `new` share at either end are left out, and the change is
    widened to whole words, so that what is shown is "isn't" becoming "is not", never
    a few letters inside a word. A character spelt composed in one and decomposed in
    the other counts as the same character.
    """
    a, b = characters(old), characters(new)
    limit = min(len(a), len(b))
    prefix = 0
    while prefix < limit and _same(a[prefix], b[prefix]):
        prefix += 1
    while prefix and not (_boundary(a, prefix) and _boundary(b, prefix)):
        prefix -= 1
    limit -= prefix
    suffix = 0
    while suffix < limit and _same(a[-1 - suffix], b[-1 - suffix]):
        suffix += 1
    while suffix and not (_boundary(a, len(a) - suffix) and _boundary(b, len(b) - suffix)):
        suffix -= 1
    start = len("".join(a[:prefix]))
    end = len(old) - len("".join(a[len(a) - suffix :]))
    return start, end, "".join(b[prefix : len(b) - suffix])


def _same(one, other):
    return one == other or nfc(one) == nfc(other)


def _boundary(chars, at):
    """Whether a cut before character number `at` falls between words, not inside one."""
    if at == 0 or at == len(chars):
        return True
    return not (_in_word(chars[at - 1]) and _in_word(chars[at]))


def _in_word(char):
    return char[0].isalnum() or char[0] in "'\u2019_"
