import json
import os

import pytest

from booktools.file_tickets import main
from tests.stubs import backlog_project, backlog_stub, only

pytestmark = pytest.mark.tier2

NASTY = 'He said "no" & `ran` $(rm -rf ~) $HOME \'x\' \\ \nsecond line \U0001f600'
TICKETS = [
    {
        "title": "Ch. 3: the 2019 figure",
        "description": NASTY,
        "priority": "medium",
        "labels": ["ch3", "fact-check-2"],
        "milestone": "First feedback",
        "status": "To Do",
        "comments": [{"author": "Claude", "text": "Source: the log"}, {"text": "A second"}],
    },
    {"title": "Only a title"},
]


class Batch:
    """A tickets file, a Backlog project and a stand-in `backlog` on a PATH of its own."""

    def __init__(self, tmp_path, monkeypatch, tickets=TICKETS, **control):
        self.project = backlog_project(tmp_path / "project")
        self.backlog = backlog_stub(tmp_path / "bin", **control)
        self.tickets = tmp_path / "tickets.json"
        self.tickets.write_text(json.dumps(tickets), encoding="utf-8")
        self.results = tmp_path / "results.json"
        monkeypatch.setenv("PATH", only(self.backlog))

    def run(self, *flags):
        return main([str(self.tickets), "--project", str(self.project), *flags])


@pytest.fixture
def batch(tmp_path, monkeypatch):
    return Batch(tmp_path, monkeypatch)


def test_files_each_ticket_then_its_comments_then_reads_it_back(batch, capsys):
    assert batch.run() == 0
    assert capsys.readouterr().out.splitlines() == [
        "TASK-1  filed  Ch. 3: the 2019 figure",
        "TASK-2  filed  Only a title",
        "2 filed, 0 failed, 0 skipped",
    ]
    assert batch.backlog.calls() == [
        ["task", "view", "--help"],
        ["task", "create", "-d", NASTY, "--priority", "medium", "-l", "ch3,fact-check-2",
         "-m", "First feedback", "-s", "To Do", "--", "Ch. 3: the 2019 figure"],
        ["task", "edit", "TASK-1", "--comment", "Source: the log", "--comment-author", "Claude"],
        ["task", "edit", "TASK-1", "--comment", "A second"],
        ["task", "view", "TASK-1", "--json"],
        ["task", "create", "--", "Only a title"],
        ["task", "view", "TASK-2", "--json"],
    ]
    # Backlog has a --project flag of its own: the folder is given as the working directory.
    assert set(batch.backlog.folders()) == {os.path.realpath(batch.project)}


def test_a_ticket_that_comes_back_different_is_reported_and_filing_goes_on(tmp_path, monkeypatch, capsys):
    batch = Batch(tmp_path, monkeypatch, mangle_create=1)
    assert batch.run() == 1
    assert capsys.readouterr().out.splitlines() == [
        "TASK-1  FAILED  Ch. 3: the 2019 figure (the description came back different)",
        "TASK-2  filed  Only a title",
        "1 filed, 1 failed, 0 skipped",
    ]


def test_a_ticket_backlog_refuses_is_reported_and_filing_goes_on(tmp_path, monkeypatch, capsys):
    batch = Batch(tmp_path, monkeypatch, fail_create=[1])
    assert batch.run() == 1
    assert capsys.readouterr().out.splitlines() == [
        "-  FAILED  Ch. 3: the 2019 figure (backlog said: Invalid status: Nonsense."
        " Valid statuses are: To Do, In Progress, Done)",
        "TASK-1  filed  Only a title",
        "1 filed, 1 failed, 0 skipped",
    ]
    # Nothing more was tried for the ticket that was not created.
    assert [call[:2] for call in batch.backlog.calls()] == [
        ["task", "view"], ["task", "create"], ["task", "create"], ["task", "view"],
    ]


@pytest.mark.parametrize("fault", ["silent_create", "garbage_create"])
def test_a_create_that_does_not_say_what_it_made_is_a_failure(tmp_path, monkeypatch, capsys, fault):
    batch = Batch(tmp_path, monkeypatch, **{fault: 1})
    assert batch.run() == 1
    assert capsys.readouterr().out.splitlines()[0] == (
        "-  FAILED  Ch. 3: the 2019 figure (backlog did not say which ticket it created;"
        " look for it in the project before filing again)"
    )


def test_a_comment_that_cannot_be_added_or_a_view_that_is_not_json_is_a_failure(
    tmp_path, monkeypatch, capsys
):
    batch = Batch(tmp_path, monkeypatch, fail_comment=True)
    assert batch.run() == 1
    assert capsys.readouterr().out.splitlines()[:2] == [
        "TASK-1  FAILED  Ch. 3: the 2019 figure (comment 1 was not added:"
        " backlog said: Could not update task)",
        "TASK-2  filed  Only a title",
    ]
    batch.backlog.control(garbage_view=True)
    assert batch.run() == 1
    assert capsys.readouterr().out.splitlines()[1] == (
        "TASK-4  FAILED  Only a title (it could not be read back to check it)"
    )
