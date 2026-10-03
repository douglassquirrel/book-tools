"""Reads an edits file: a JSON list of changes to propose."""

import json
import re
import unicodedata

KEYS = ("id", "where", "find", "replace", "occurrence", "why")
WHERE = re.compile(r"(body|all|(endnote|footnote):[1-9][0-9]*)$")


class EditsFileError(Exception):
    """The edits file cannot be used. `problems` lists every fault found in it."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = problems


class Edit:
    def __init__(self, index, id, where, find, replace, occurrence, why):
        self.index = index  # position in the file, from 1
        self.id = id
        self.where = where  # ("body",), ("all",), ("endnote", N) or ("footnote", N)
        self.find = find
        self.replace = replace
        self.occurrence = occurrence  # None when not given
        self.why = why

    @property
    def name(self):
        """How messages refer to this edit."""
        return f"edit {self.index} ({self.id})" if self.id else f"edit {self.index}"


def parse_edits(text):
    """Return the Edits in `text`, or raise EditsFileError naming every fault."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        where = f"line {error.lineno}, column {error.colno}"
        raise EditsFileError([f"not valid JSON: {error.msg} ({where})"]) from None
    if not isinstance(data, list):
        raise EditsFileError(["the edits file must hold a JSON list of edits"])
    edits = []
    problems = []
    for index, item in enumerate(data, 1):
        if not isinstance(item, dict):
            problems.append(f'edit {index}: must be an object with "find" and "replace"')
            continue
        id = item.get("id", "")
        name = f"edit {index} ({id})" if id and isinstance(id, str) else f"edit {index}"
        faults = _faults(item)
        problems.extend(f"{name}: {fault}" for fault in faults)
        if not faults:
            edits.append(
                Edit(
                    index,
                    id,
                    _where(item.get("where", "body")),
                    item["find"],
                    item["replace"],
                    item.get("occurrence"),
                    item.get("why", ""),
                )
            )
    if problems:
        raise EditsFileError(problems)
    return edits


def _faults(item):
    """Everything wrong with one edit, in words for the person who wrote the file."""
    faults = [f'unknown key "{key}"' for key in item if key not in KEYS]
    for key in ("id", "why"):
        if not isinstance(item.get(key, ""), str):
            faults.append(f'"{key}" must be text')
    find, replace = item.get("find"), item.get("replace")
    if not isinstance(find, str) or not find:
        faults.append('"find" must be text and not empty')
        find = None
    if not isinstance(replace, str):
        faults.append('"replace" must be text (empty to delete)')
        replace = None
    if find is not None and replace is not None:
        nfc = unicodedata.normalize
        if nfc("NFC", find) == nfc("NFC", replace):
            faults.append('"replace" is the same as "find", so the edit would change nothing')
    for key, value in (("find", find), ("replace", replace)):
        if value is None:
            continue
        if "\n" in value or "\r" in value:
            faults.append(
                f'"{key}" holds a line break; an edit must stay within one paragraph'
                " (join or split paragraphs by hand in Word)"
            )
        if "\t" in value:
            faults.append(f'"{key}" holds a tab, which cannot be proposed as a tracked change here')
    where = item.get("where", "body")
    if not isinstance(where, str) or not WHERE.match(where):
        faults.append('"where" must be body, all, endnote:N or footnote:N (N from 1)')
    occurrence = item.get("occurrence", 1)
    if type(occurrence) is not int or occurrence < 1:
        faults.append('"occurrence" must be a whole number, 1 or more')
    return faults


def _where(value):
    """("body",), ("all",), ("endnote", N) or ("footnote", N) for the text of "where"."""
    kind, _, number = value.partition(":")
    return (kind, int(number)) if number else (kind,)
