"""Finds the sentence a note's marker belongs to."""

import re

STOP = re.compile(r"[.!?]+[\"'\u201d\u2019)\]]*(?=\s|$)")
WORD_BEFORE = re.compile(r"[^\W\d_]+$")
OPENERS = "\"'\u201c\u2018(["
ABBREVIATIONS = {
    "Dr", "Mr", "Mrs", "Ms", "Prof", "St", "Sr", "Jr", "vs", "cf", "Vol", "Ch",
    "Fig", "ed", "eds", "trans", "pp",
}  # fmt: skip
# "No." is left out on purpose: before a number it is followed by a digit, which
# never starts a sentence here, and otherwise it is the word "No".


def sentence_at(text, offset):
    """The sentence of `text` that a note marker standing at `offset` belongs to.

    A marker straight after a full stop belongs to the sentence that has just ended;
    a marker in mid-sentence belongs to the sentence around it.
    """
    spans = _sentences(text)
    if not spans:
        return ""
    chosen = spans[0]
    for start, end in spans:
        if start < offset:
            chosen = (start, end)
    return text[chosen[0] : chosen[1]].strip()


def _sentences(text):
    """(start, end) of each sentence of `text`.

    A sentence ends at a stop, question mark or exclamation mark (with any closing
    quotation marks or brackets after it) that is followed by white space and then
    a capital letter or an opening quotation mark, or by the end of the text. A stop
    after a common abbreviation or a single initial does not end one.
    """
    spans = []
    start = 0
    for stop in STOP.finditer(text):
        rest = text[stop.end() :].lstrip()
        if rest and not (rest[0].isupper() or rest[0] in OPENERS):
            continue
        word = WORD_BEFORE.search(text[: stop.start()])
        if word and (word.group(0) in ABBREVIATIONS or len(word.group(0)) == 1):
            continue
        spans.append((start, stop.end()))
        start = len(text) - len(rest)
    if text[start:].strip():
        spans.append((start, len(text)))
    return spans
