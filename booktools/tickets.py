"""Tickets to file into Backlog: reading the tickets file, building each `backlog`
command, and checking what came back."""

import json
import re

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


def create_command(ticket):
    """The `backlog` command, as an argument list, that creates `ticket`.

    Options come first and the title last, after "--", so that a title or a
    description beginning with a dash is not taken for an option.
    """
    command = ["backlog", "task", "create"]
    if ticket.description is not None:
        command += ["-d", ticket.description]
    if ticket.priority:
        command += ["--priority", ticket.priority]
    if ticket.labels:
        command += ["-l", ",".join(ticket.labels)]
    if ticket.milestone:
        command += ["-m", ticket.milestone]
    if ticket.status:
        command += ["-s", ticket.status]
    return command + ["--", ticket.title]


def comment_command(id, author, text):
    """The command that adds one comment to the ticket with this id."""
    command = ["backlog", "task", "edit", id, "--comment", text]
    return command + ["--comment-author", author] if author else command


def view_command(id):
    """The command that reads the ticket back as JSON."""
    return ["backlog", "task", "view", id, "--json"]


def created_id(output):
    """The id of the ticket `backlog task create` said it made, or None."""
    found = re.search(r"^Created task (\S+)", output, re.M)
    return found.group(1) if found else None


def tidy(text):
    """`text` as Backlog stores a description or a comment: both ends trimmed, CRLF
    made LF, and a run of blank lines made one."""
    return re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n")).strip()


def mismatches(ticket, viewed):
    """What differs between `ticket` as sent and `viewed`, the "task" object that
    `backlog task view --json` returned for it. An empty list means it arrived whole."""
    found = []
    if viewed.get("title") != ticket.title:
        found.append("the title came back different")
    sent = tidy(ticket.description) if ticket.description is not None else ""
    if (viewed.get("description") or "") != sent:
        found.append("the description came back different")
    if ticket.priority and (viewed.get("priority") or "").lower() != ticket.priority:
        found.append(f"the priority came back as {viewed.get('priority') or 'nothing'}")
    if ticket.labels and viewed.get("labels") != ticket.labels:
        labels = ", ".join(viewed.get("labels") or []) or "nothing"
        found.append(f"the labels came back as {labels}")
    for name, wanted in (("milestone", ticket.milestone), ("status", ticket.status)):
        got = viewed.get(name)
        if wanted and (got or "").casefold() != wanted.casefold():
            found.append(f"the {name} came back as {got or 'nothing'}")
    comments = viewed.get("comments") or []
    if len(comments) != len(ticket.comments):
        count = "1 comment" if len(comments) == 1 else f"{len(comments)} comments"
        found.append(f"{count} came back where {len(ticket.comments)} were sent")
        return found
    for number, ((author, text), got) in enumerate(zip(ticket.comments, comments), 1):
        if got.get("body") != tidy(text):
            found.append(f"comment {number} came back different")
        if (got.get("author") or None) != author:
            found.append(f"the author of comment {number} came back different")
    return found


class ResultsError(Exception):
    """The results file cannot be used with this tickets file."""


def dump_results(records):
    """The text of a results file: one record per ticket dealt with so far."""
    return json.dumps(records, indent=2, ensure_ascii=False) + "\n"


def load_results(text, tickets):
    """Return {index: record} from a results file's text, for resuming `tickets`.

    Raises ResultsError if the text is not a results file, or if a record's title is
    not the title of the ticket at that index: it belongs to another tickets file.
    """
    try:
        records = json.loads(text)
        if not isinstance(records, list):
            raise TypeError
        found = {record["index"]: record for record in records}
        for record in records:
            record["title"], record["id"], record["outcome"]
    except (ValueError, TypeError, KeyError):
        raise ResultsError("it is not a results file written by file-tickets") from None
    for index, record in found.items():
        if not isinstance(index, int) or not 1 <= index <= len(tickets):
            raise ResultsError(
                f"it has a record for ticket {index} but the tickets file holds {len(tickets)}"
            )
        title = tickets[index - 1].title
        if record["title"] != title:
            raise ResultsError(
                f'the record for ticket {index} is titled "{record["title"]}"'
                f' but that ticket is titled "{title}"'
            )
    return found
