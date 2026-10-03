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
