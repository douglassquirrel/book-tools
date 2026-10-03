"""Text as a reader sees it: whole characters, however Unicode spells them."""

import difflib
import re
import unicodedata

WORD = re.compile(r"\w+")


def characters(text):
    """Split `text` into whole characters: a letter together with its accents, or a
    Hangul syllable written as separate jamo, is one."""
    found = []
    current = ""
    for char in text:
        if current and _stands_alone(current, char):
            found.append(current)
            current = ""
        current += char
    if current:
        found.append(current)
    return found


def nfc(text):
    return unicodedata.normalize("NFC", text)


def _stands_alone(before, char):
    """Whether `char` stands by itself after `before` rather than combining with it."""
    if char.isascii() and before.isascii():
        return True
    if unicodedata.combining(char):
        return False
    return nfc(before + char) == nfc(before) + nfc(char)


def likeness(one, other):
    """How alike two pieces of text are, from 0 to 1, comparing them word by word."""
    a, b = WORD.findall(one.lower()), WORD.findall(other.lower())
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
