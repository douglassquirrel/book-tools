import json

import pytest

from booktools.tickets import TicketsFileError, parse_tickets

pytestmark = pytest.mark.tier1

FULL = {
    "title": "Ch. 3: Table 3.1 row 4 cites the 2019 figure",
    "description": "## Current state\n\n**Book now says:** 12 pints",
    "priority": "medium",
    "labels": ["ch3", "fact-check-2"],
    "milestone": "First feedback",
    "status": "To Do",
    "comments": [{"author": "Claude", "text": "Source: the log"}, {"text": "No author here"}],
}


def fields(t):
    return (t.index, t.title, t.description, t.priority, t.labels, t.milestone, t.status, t.comments)


def test_reads_every_field_of_a_ticket():
    (ticket,) = parse_tickets(json.dumps([FULL]))
    assert fields(ticket) == (
        1,
        "Ch. 3: Table 3.1 row 4 cites the 2019 figure",
        "## Current state\n\n**Book now says:** 12 pints",
        "medium",
        ["ch3", "fact-check-2"],
        "First feedback",
        "To Do",
        [("Claude", "Source: the log"), (None, "No author here")],
    )


def test_a_ticket_may_have_only_a_title():
    first, second = parse_tickets('[{"title": "One"}, {"title": "Two", "priority": "HIGH"}]')
    assert fields(first) == (1, "One", None, None, [], None, None, [])
    assert (second.index, second.priority) == (2, "high")
    assert parse_tickets("[]") == []


def problems(text):
    with pytest.raises(TicketsFileError) as caught:
        parse_tickets(text)
    return caught.value.problems


def one(**item):
    return json.dumps([item])


def test_a_file_that_is_not_a_json_list_of_objects_is_refused():
    assert problems("nope")[0].startswith("not valid JSON: ")
    assert problems('{"title": "x"}') == ["the tickets file must hold a JSON list of tickets"]
    assert problems('["x"]') == ['ticket 1: must be an object with a "title"']


def test_every_fault_in_a_ticket_is_named():
    assert problems(one(description="no title")) == ['ticket 1: "title" must be text and not empty']
    assert problems(one(title="a\nb")) == ['ticket 1: "title" must be on one line']
    assert problems(one(title="T", priority="urgent")) == [
        'ticket 1 (T): "priority" must be high, medium or low'
    ]
    assert problems(one(title="T", labels="ch3")) == [
        'ticket 1 (T): "labels" must be a list of texts, none holding a comma'
    ]
    assert problems(one(title="T", labels=["a,b"])) == [
        'ticket 1 (T): "labels" must be a list of texts, none holding a comma'
    ]
    assert problems(one(title="T", comments=[{"author": "A"}])) == [
        'ticket 1 (T): each of "comments" must be an object with "text" and, if wished, "author"'
    ]
    assert problems(one(title="T", comments=[{"text": "x", "by": "A"}])) == [
        'ticket 1 (T): each of "comments" must be an object with "text" and, if wished, "author"'
    ]
    text = json.dumps([{"title": "T", "tittle": "x", "status": 3, "milestone": "", "description": 1}])
    assert problems(text) == [
        'ticket 1 (T): unknown key "tittle"',
        'ticket 1 (T): "description" must be text',
        'ticket 1 (T): "milestone" must be text and not empty',
        'ticket 1 (T): "status" must be text and not empty',
    ]


def test_the_create_command_passes_each_field_as_one_argument_with_the_title_last():
    from booktools.tickets import create_command

    (ticket,) = parse_tickets(json.dumps([FULL]))
    assert create_command(ticket) == [
        "backlog", "task", "create",
        "-d", "## Current state\n\n**Book now says:** 12 pints",
        "--priority", "medium",
        "-l", "ch3,fact-check-2",
        "-m", "First feedback",
        "-s", "To Do",
        "--", "Ch. 3: Table 3.1 row 4 cites the 2019 figure",
    ]


def test_fields_not_given_are_left_out_of_the_command():
    from booktools.tickets import create_command

    (ticket,) = parse_tickets('[{"title": "-5 degrees"}]')
    assert create_command(ticket) == ["backlog", "task", "create", "--", "-5 degrees"]


def test_awkward_characters_reach_the_command_untouched():
    from booktools.tickets import create_command

    nasty = 'He said "no" & `ran` $(rm -rf ~) \'x\' \\ \n\ttab \U0001f600'
    (ticket,) = parse_tickets(json.dumps([{"title": "T", "description": nasty}]))
    assert create_command(ticket)[4] == nasty


def test_comment_and_view_commands():
    from booktools.tickets import comment_command, view_command

    assert comment_command("TASK-7", "Claude", "Source: the log") == [
        "backlog", "task", "edit", "TASK-7", "--comment", "Source: the log",
        "--comment-author", "Claude",
    ]
    assert comment_command("TASK-7", None, "-x") == [
        "backlog", "task", "edit", "TASK-7", "--comment", "-x",
    ]
    assert view_command("TASK-7") == ["backlog", "task", "view", "TASK-7", "--json"]


def test_reads_the_new_id_from_what_create_printed():
    from booktools.tickets import created_id

    assert created_id("Created task TASK-408\nFile: /x/backlog/tasks/task-408 - T.md\n") == "TASK-408"
    assert created_id("Created task FC-12") == "FC-12"
    assert created_id("No Backlog.md project found. Run `backlog init` to initialize.\n") is None
    assert created_id("") is None
