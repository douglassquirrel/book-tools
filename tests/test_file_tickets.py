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


def refused(batch, capsys, *flags):
    """Run expecting a refusal to start: exit 2, nothing printed, no ticket created."""
    assert batch.run(*flags) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert ["task", "create"] not in [call[:2] for call in batch.backlog.calls()]
    return captured.err.splitlines()


def test_refuses_to_start_when_backlog_is_not_installed_and_says_how_to_install_it(
    batch, capsys, monkeypatch, tmp_path
):
    empty = tmp_path / "nothing-here"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert refused(batch, capsys) == [
        "file-tickets: the backlog command was not found. Backlog is yours to install:"
        " brew install backlog-md (or: npm i -g backlog.md)"
    ]


def test_refuses_a_folder_that_is_not_a_backlog_project(batch, capsys):
    (batch.project / "backlog" / "config.yml").unlink()
    assert refused(batch, capsys) == [
        f"file-tickets: {batch.project} is not a Backlog project (it has no backlog/config.yml);"
        " run backlog init there first"
    ]


def test_refuses_a_backlog_whose_view_has_no_json(tmp_path, monkeypatch, capsys):
    batch = Batch(tmp_path, monkeypatch, no_json=True)
    assert refused(batch, capsys) == [
        "file-tickets: this backlog has no `task view --json`, which is needed to check each"
        " ticket; the kit was tested with Backlog 1.53.0"
    ]


def test_refuses_a_missing_or_faulty_tickets_file(batch, capsys):
    batch.tickets.write_text('[{"title": ""}, {"title": "T", "priority": "urgent"}]')
    assert refused(batch, capsys) == [
        f"file-tickets: {batch.tickets} cannot be used:",
        '  ticket 1: "title" must be text and not empty',
        '  ticket 2 (T): "priority" must be high, medium or low',
    ]
    batch.tickets.unlink()
    assert refused(batch, capsys) == [f"file-tickets: {batch.tickets}: no such file"]


def test_an_empty_tickets_file_succeeds_and_files_nothing(tmp_path, monkeypatch, capsys):
    batch = Batch(tmp_path, monkeypatch, tickets=[])
    assert batch.run() == 0
    assert capsys.readouterr().out == "no tickets, nothing filed\n"
    assert batch.backlog.calls() == []


def test_a_usage_error_exits_2_and_help_exits_0(capsys):
    assert main(["--project"]) == 2
    assert "usage: file-tickets" in capsys.readouterr().err
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    for flag in ("TICKETS.json", "--project", "--dry-run", "--results", "--skip-existing",
                 "--ignore-locks", "--timeout"):
        assert flag in out


def test_dry_run_prints_each_command_quoted_for_reading_and_runs_nothing(batch, capsys, monkeypatch, tmp_path):
    empty = tmp_path / "nothing-here"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))  # a dry run does not need backlog at all
    assert batch.run("--dry-run", "--skip-existing") == 0
    quoted = "'He said \"no\" & `ran` $(rm -rf ~) $HOME '\"'\"'x'\"'\"' \\ \nsecond line \U0001f600'"
    assert capsys.readouterr().out == "\n".join(
        [
            "backlog task list --json",
            f"backlog task create -d {quoted} --priority medium -l ch3,fact-check-2"
            " -m 'First feedback' -s 'To Do' -- 'Ch. 3: the 2019 figure'",
            "backlog task edit ID --comment 'Source: the log' --comment-author Claude",
            "backlog task edit ID --comment 'A second'",
            "backlog task view ID --json",
            "backlog task create -- 'Only a title'",
            "backlog task view ID --json",
            f"dry run: 2 tickets would be filed in {batch.project}; nothing run",
            "",
        ]
    )
    assert batch.backlog.calls() == []


def records(batch):
    return json.loads(batch.results.read_text(encoding="utf-8"))


def test_results_are_written_as_the_batch_goes_and_a_second_run_files_nothing_twice(
    tmp_path, monkeypatch, capsys
):
    three = TICKETS + [{"title": "A third"}]
    batch = Batch(tmp_path, monkeypatch, tickets=three, fail_create=[2])
    assert batch.run("--results", str(batch.results)) == 1
    assert capsys.readouterr().out.splitlines()[-1] == "2 filed, 1 failed, 0 skipped"
    assert records(batch) == [
        {"index": 1, "title": "Ch. 3: the 2019 figure", "id": "TASK-1", "outcome": "filed"},
        {"index": 2, "title": "Only a title", "id": None,
         "outcome": "failed: backlog said: Invalid status: Nonsense."
         " Valid statuses are: To Do, In Progress, Done"},
        {"index": 3, "title": "A third", "id": "TASK-2", "outcome": "filed"},
    ]

    batch.backlog.control()  # backlog is well again
    assert batch.run("--results", str(batch.results)) == 0
    assert capsys.readouterr().out.splitlines() == [
        "TASK-1  already filed  Ch. 3: the 2019 figure",
        "TASK-3  filed  Only a title",
        "TASK-2  already filed  A third",
        "1 filed, 0 failed, 2 skipped",
    ]
    assert [r["outcome"] for r in records(batch)] == ["filed", "filed", "filed"]
    creates = [call for call in batch.backlog.calls() if call[:2] == ["task", "create"]]
    assert [call[-1] for call in creates] == [
        "Ch. 3: the 2019 figure", "Only a title", "A third", "Only a title",
    ]


def test_a_ticket_created_earlier_but_not_confirmed_is_never_created_again(
    tmp_path, monkeypatch, capsys
):
    batch = Batch(tmp_path, monkeypatch, mangle_create=1)
    assert batch.run("--results", str(batch.results)) == 1
    capsys.readouterr()
    batch.backlog.control()
    assert batch.run("--results", str(batch.results)) == 1
    assert capsys.readouterr().out.splitlines() == [
        "TASK-1  FAILED  Ch. 3: the 2019 figure (created in an earlier run and not filed again;"
        " then: the description came back different)",
        "TASK-2  already filed  Only a title",
        "0 filed, 1 failed, 1 skipped",
    ]
    assert len([c for c in batch.backlog.calls() if c[:2] == ["task", "create"]]) == 2


def test_a_results_file_from_another_batch_is_refused_and_nothing_is_filed(batch, capsys):
    batch.results.write_text('[{"index": 1, "title": "Other", "id": "TASK-9", "outcome": "filed"}]')
    assert refused(batch, capsys, "--results", str(batch.results)) == [
        f"file-tickets: {batch.results} does not fit {batch.tickets}:"
        ' the record for ticket 1 is titled "Other" but that ticket is titled'
        ' "Ch. 3: the 2019 figure"'
    ]


def test_without_results_no_file_is_written(batch, tmp_path):
    before = sorted(path.name for path in tmp_path.iterdir())
    assert batch.run() == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == before


def test_skip_existing_leaves_out_a_ticket_whose_exact_title_is_already_there(batch, capsys):
    assert batch.run() == 0  # both tickets are now in the project
    capsys.readouterr()
    batch.tickets.write_text(json.dumps([{"title": "Only a title"}, {"title": "Only a title."}]))
    assert batch.run("--skip-existing") == 0
    assert capsys.readouterr().out.splitlines() == [
        "TASK-2  skipped  Only a title (a ticket with this title exists)",
        "TASK-3  filed  Only a title.",
        "1 filed, 0 failed, 1 skipped",
    ]
    assert batch.backlog.calls()[-4:] == [
        ["task", "view", "--help"],
        ["task", "list", "--json"],
        ["task", "create", "--", "Only a title."],
        ["task", "view", "TASK-3", "--json"],
    ]


def test_without_skip_existing_a_duplicate_title_is_filed(batch, capsys):
    assert batch.run() == 0
    assert batch.run() == 0
    assert capsys.readouterr().out.splitlines()[-3:] == [
        "TASK-3  filed  Ch. 3: the 2019 figure",
        "TASK-4  filed  Only a title",
        "2 filed, 0 failed, 0 skipped",
    ]


def test_skip_existing_refuses_to_go_on_if_the_project_cannot_be_listed(tmp_path, monkeypatch, capsys):
    batch = Batch(tmp_path, monkeypatch)
    source = (batch.backlog.folder / "backlog").read_text()
    (batch.backlog.folder / "backlog").write_text(
        source.replace('print(json.dumps({"schemaVersion": 1, "kind": "task-list"', 'print(("oops", {"k": 1, "kind": "task-list"')
    )
    assert refused(batch, capsys, "--skip-existing") == [
        "file-tickets: the project's tickets could not be listed (backlog task list --json"
        " did not print what was expected), so --skip-existing cannot be relied on"
    ]


def test_a_lock_left_in_the_project_stops_the_batch_before_it_starts(batch, capsys):
    lock = batch.project / "backlog" / ".locks" / "task-7"
    lock.mkdir(parents=True)
    assert refused(batch, capsys) == [
        "file-tickets: Backlog has left a lock in the project: backlog/.locks/task-7."
        " Make sure no backlog command is running, remove it by hand, or add --ignore-locks"
    ]
    assert lock.is_dir()  # never removed by the kit
    assert batch.run("--ignore-locks") == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "file-tickets: a lock is still in the project: backlog/.locks/task-7 (not removed)"
    ]
    assert lock.is_dir()


def test_an_empty_locks_folder_is_not_a_lock(batch):
    (batch.project / "backlog" / ".locks").mkdir()
    assert batch.run() == 0


def test_a_lock_left_behind_during_the_batch_is_reported_and_never_removed(tmp_path, monkeypatch, capsys):
    batch = Batch(tmp_path, monkeypatch, leave_lock=True)
    assert batch.run() == 0
    assert capsys.readouterr().err.splitlines() == [
        "file-tickets: 2 locks are still in the project: backlog/.locks/task-1,"
        " backlog/.locks/task-2 (not removed)"
    ]
    assert sorted(p.name for p in (batch.project / "backlog" / ".locks").iterdir()) == [
        "task-1", "task-2",
    ]


def test_a_backlog_that_does_not_answer_in_time_stops_the_whole_batch(tmp_path, monkeypatch, capsys):
    three = TICKETS + [{"title": "A third"}]
    batch = Batch(tmp_path, monkeypatch, tickets=three, hang_on_create=2)
    assert batch.run("--timeout", "3", "--results", str(batch.results)) == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "TASK-1  filed  Ch. 3: the 2019 figure",
        "-  FAILED  Only a title (backlog did not answer within 3 seconds)",
        "1 filed, 1 failed, 0 skipped; stopped with 1 ticket not tried",
    ]
    assert captured.err.splitlines() == [
        "file-tickets: stopped: going on could file tickets twice or out of order."
        " Check the project for 'Only a title', then run again with the same --results file"
    ]
    assert [r["outcome"] for r in records(batch)] == [
        "filed", "failed: backlog did not answer within 3 seconds",
    ]
    creates = [call for call in batch.backlog.calls() if call[:2] == ["task", "create"]]
    assert len(creates) == 2  # the third ticket was never tried


def test_an_interrupted_batch_keeps_its_results_and_exits_130(batch, capsys, monkeypatch):
    import booktools.file_tickets as command

    real = command._file

    def interrupted_on_the_second(ticket, project, timeout):
        if ticket.index == 2:
            raise KeyboardInterrupt
        return real(ticket, project, timeout)

    monkeypatch.setattr(command, "_file", interrupted_on_the_second)
    assert batch.run("--results", str(batch.results)) == 130
    assert capsys.readouterr().err.splitlines() == [
        "file-tickets: interrupted; run again with the same --results file to finish the batch"
    ]
    assert [(r["index"], r["outcome"]) for r in records(batch)] == [(1, "filed")]
    assert sorted(p.name for p in batch.results.parent.iterdir() if "partial" in p.name) == []


def test_a_backlog_that_does_not_answer_the_first_question_is_a_refusal(tmp_path, monkeypatch, capsys):
    batch = Batch(tmp_path, monkeypatch, hang_on_help=True)
    assert refused(batch, capsys, "--timeout", "2") == [
        "file-tickets: backlog did not answer within 2 seconds"
    ]


def test_a_create_that_dies_without_a_word_is_reported_with_its_exit_code(tmp_path, monkeypatch, capsys):
    batch = Batch(tmp_path, monkeypatch, create_dies_silently=True)
    assert batch.run() == 1
    assert capsys.readouterr().out.splitlines()[0] == (
        "-  FAILED  Ch. 3: the 2019 figure (backlog said: nothing, and exited 3)"
    )


def test_a_part_written_results_file_that_cannot_be_removed_is_reported_not_a_traceback(
    batch, capsys, monkeypatch
):
    import os

    from tests.stubs import forbid_removal

    def interrupt(source, target):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "replace", interrupt)
    forbid_removal(monkeypatch, ".partial-")
    assert batch.run("--results", str(batch.results)) == 130
    assert capsys.readouterr().err.splitlines() == [
        "file-tickets: could not remove the part-written file"
        f" {batch.results}.partial-{os.getpid()}: Operation not permitted; remove it by hand",
        "file-tickets: interrupted; run again with the same --results file to finish the batch",
    ]
