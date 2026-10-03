"""Reads an edits file: a JSON list of changes to propose."""

import json


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
    edits = []
    for index, item in enumerate(json.loads(text), 1):
        edits.append(
            Edit(
                index,
                item.get("id", ""),
                _where(item.get("where", "body")),
                item["find"],
                item["replace"],
                item.get("occurrence"),
                item.get("why", ""),
            )
        )
    return edits


def _where(value):
    """("body",), ("all",), ("endnote", N) or ("footnote", N) for the text of "where"."""
    kind, _, number = value.partition(":")
    return (kind, int(number)) if number else (kind,)
