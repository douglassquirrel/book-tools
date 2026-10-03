"""Works out which part of an edit actually changes."""

import unicodedata


def common_ends(old, new):
    """Return (prefix, suffix): how many characters at each end `old` and `new` share
    and can be left unmarked. Both ends stop at word boundaries, so that the
    change shown is whole words, never a few letters inside one."""
    limit = min(len(old), len(new))
    prefix = 0
    while prefix < limit and old[prefix] == new[prefix]:
        prefix += 1
    while prefix and not (_boundary(old, prefix) and _boundary(new, prefix)):
        prefix -= 1
    limit -= prefix
    suffix = 0
    while suffix < limit and old[-1 - suffix] == new[-1 - suffix]:
        suffix += 1
    while suffix and not (
        _boundary(old, len(old) - suffix) and _boundary(new, len(new) - suffix)
    ):
        suffix -= 1
    return prefix, suffix


def _boundary(text, at):
    """Whether a cut at offset `at` falls between words rather than inside one."""
    if at == 0 or at == len(text):
        return True
    return not (_in_word(text[at - 1]) and _in_word(text[at]))


def _in_word(char):
    return char.isalnum() or char in "'’_" or bool(unicodedata.combining(char))
