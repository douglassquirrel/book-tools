"""Tickets to file into Backlog: reading the tickets file, building each `backlog`
command, and checking what came back."""

import json

KEYS = ("title", "description", "priority", "labels", "milestone", "status", "comments")


class TicketsFileError(Exception):
    """The tickets file cannot be used. `problems` lists every fault found in it."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = problems


class Ticket:
    def __init__(self, index, title, description, priority, labels, milestone, status, comments):
        self.index = index  # position in the file, from 1
        self.title = title
        self.description = description  # None when not given
        self.priority = priority
        self.labels = labels  # a list, possibly empty
        self.milestone = milestone
        self.status = status
        self.comments = comments  # (author or None, text) pairs, in order


def parse_tickets(text):
    """Return the Tickets in `text`, or raise TicketsFileError naming every fault."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        where = f"line {error.lineno}, column {error.colno}"
        raise TicketsFileError([f"not valid JSON: {error.msg} ({where})"]) from None
    if not isinstance(data, list):
        raise TicketsFileError(["the tickets file must hold a JSON list of tickets"])
    tickets = []
    problems = []
    for index, item in enumerate(data, 1):
        if not isinstance(item, dict):
            problems.append(f'ticket {index}: must be an object with a "title"')
            continue
        title = item.get("title")
        faults = _faults(item)
        named = isinstance(title, str) and title and "\n" not in title
        name = f"ticket {index} ({title})" if named else f"ticket {index}"
        problems.extend(f"{name}: {fault}" for fault in faults)
        if not faults:
            priority = item.get("priority")
            comments = [(c.get("author"), c["text"]) for c in item.get("comments", [])]
            tickets.append(
                Ticket(
                    index,
                    title,
                    item.get("description"),
                    priority.lower() if priority else None,
                    list(item.get("labels", [])),
                    item.get("milestone"),
                    item.get("status"),
                    comments,
                )
            )
    if problems:
        raise TicketsFileError(problems)
    return tickets


def _faults(item):
    """Everything wrong with one ticket, in words for the person who wrote the file."""
    faults = [f'unknown key "{key}"' for key in item if key not in KEYS]
    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        faults.append('"title" must be text and not empty')
    elif "\n" in title or "\r" in title:
        faults.append('"title" must be on one line')
    if not isinstance(item.get("description", ""), str):
        faults.append('"description" must be text')
    priority = item.get("priority", "low")
    if not isinstance(priority, str) or priority.lower() not in ("high", "medium", "low"):
        faults.append('"priority" must be high, medium or low')
    labels = item.get("labels", [])
    if not isinstance(labels, list) or not all(
        isinstance(label, str) and label and "," not in label for label in labels
    ):
        faults.append('"labels" must be a list of texts, none holding a comma')
    for key in ("milestone", "status"):
        value = item.get(key, "x")
        if not isinstance(value, str) or not value:
            faults.append(f'"{key}" must be text and not empty')
    comments = item.get("comments", [])
    if not isinstance(comments, list) or not all(_is_comment(c) for c in comments):
        faults.append(
            'each of "comments" must be an object with "text" and, if wished, "author"'
        )
    return faults


def _is_comment(value):
    return (
        isinstance(value, dict)
        and isinstance(value.get("text"), str)
        and bool(value["text"])
        and isinstance(value.get("author", ""), str)
        and set(value) <= {"text", "author"}
    )
