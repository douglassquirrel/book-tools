"""file-tickets: file tickets into a Backlog project from a JSON list."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys

from booktools import cli
from booktools.cli import Refusal
from booktools.tickets import (
    ResultsError,
    TicketsFileError,
    comment_command,
    create_command,
    created_id,
    dump_results,
    load_results,
    mismatches,
    parse_tickets,
    view_command,
)

TESTED_WITH = "1.53.0"
LIST = ["backlog", "task", "list", "--json"]
STALLED = "backlog did not answer"


def main(argv=None):
    """Run the command; return its exit code."""
    return cli.run(
        "file-tickets",
        _parser(),
        _run,
        argv,
        interrupted="interrupted; run again with the same --results file to finish the batch",
    )


def _run(args):
    try:
        with open(args.tickets, encoding="utf-8") as file:
            tickets = parse_tickets(file.read())
    except FileNotFoundError:
        raise Refusal(f"{args.tickets}: no such file") from None
    except TicketsFileError as error:
        raise Refusal(f"{args.tickets} cannot be used:", *error.problems) from None
    if not tickets:
        print("no tickets, nothing filed")
        return 0
    records = {}
    if args.results and os.path.exists(args.results):
        try:
            with open(args.results, encoding="utf-8") as file:
                records = load_results(file.read(), tickets)
        except ResultsError as error:
            raise Refusal(f"{args.results} does not fit {args.tickets}: {error}") from None
    if not os.path.isfile(os.path.join(args.project, "backlog", "config.yml")):
        raise Refusal(
            f"{args.project} is not a Backlog project (it has no backlog/config.yml);"
            " run backlog init there first"
        )
    locks = _locks(args.project)
    if locks and not args.ignore_locks:
        raise Refusal(
            f"Backlog has left a lock in the project: {', '.join(locks)}."
            " Make sure no backlog command is running, remove it by hand, or add --ignore-locks"
        )
    if args.dry_run:
        if args.skip_existing:
            print(shlex.join(LIST))
        for ticket in tickets:
            print(shlex.join(create_command(ticket)))
            for author, text in ticket.comments:
                print(shlex.join(comment_command("ID", author, text)))
            print(shlex.join(view_command("ID")))
        count = "1 ticket" if len(tickets) == 1 else f"{len(tickets)} tickets"
        print(f"dry run: {count} would be filed in {args.project}; nothing run")
        return 0
    if shutil.which("backlog") is None:
        raise Refusal(
            "the backlog command was not found. Backlog is yours to install:"
            " brew install backlog-md (or: npm i -g backlog.md)"
        )
    try:
        can_view = _backlog(["backlog", "task", "view", "--help"], args.project, args.timeout)
        existing = _titles(args.project, args.timeout) if args.skip_existing else {}
    except subprocess.TimeoutExpired:
        raise Refusal(f"backlog did not answer within {args.timeout:g} seconds") from None
    if "--json" not in can_view.stdout:
        raise Refusal(
            "this backlog has no `task view --json`, which is needed to check each"
            f" ticket; the kit was tested with Backlog {TESTED_WITH}"
        )
    filed = failed = skipped = 0
    stalled = None
    tried = 0
    for ticket in tickets:
        tried += 1
        earlier = records.get(ticket.index)
        if earlier and earlier["id"] and earlier["outcome"] != "skipped":
            # It exists in Backlog already: never create it a second time.
            if earlier["outcome"] == "filed":
                skipped += 1
                print(f"{earlier['id']}  already filed  {ticket.title}")
            else:
                failed += 1
                then = earlier["outcome"].replace("failed: ", "", 1)
                print(
                    f"{earlier['id']}  FAILED  {ticket.title}"
                    f" (created in an earlier run and not filed again; then: {then})"
                )
            continue
        if ticket.title in existing:
            id, outcome = existing[ticket.title], "skipped"
            skipped += 1
            print(f"{id}  skipped  {ticket.title} (a ticket with this title exists)")
        else:
            id, fault = _file(ticket, args.project, args.timeout)
            outcome = f"failed: {fault}" if fault else "filed"
            if fault and fault.startswith(STALLED):
                stalled = ticket
            if fault:
                failed += 1
                print(f"{id or '-'}  FAILED  {ticket.title} ({fault})")
            else:
                filed += 1
                print(f"{id}  filed  {ticket.title}")
            if id and args.skip_existing:
                existing[ticket.title] = id
        records[ticket.index] = {
            "index": ticket.index,
            "title": ticket.title,
            "id": id,
            "outcome": outcome,
        }
        _save(args.results, records)
        if stalled:
            break
    summary = f"{filed} filed, {failed} failed, {skipped} skipped"
    if stalled:
        left = len(tickets) - tried
        summary += f"; stopped with {left} ticket{'' if left == 1 else 's'} not tried"
        print(
            "file-tickets: stopped: going on could file tickets twice or out of order."
            f" Check the project for '{stalled.title}', then run again with the same"
            " --results file",
            file=sys.stderr,
        )
    print(summary)
    locks = _locks(args.project)
    if locks:
        count = "a lock is" if len(locks) == 1 else f"{len(locks)} locks are"
        still = f"{count} still in the project: {', '.join(locks)} (not removed)"
        print(f"file-tickets: {still}", file=sys.stderr)
    return 1 if failed else 0


def _locks(project):
    """The locks Backlog has left in the project. The kit never removes one."""
    folder = os.path.join(project, "backlog", ".locks")
    if not os.path.isdir(folder):
        return []
    return [f"backlog/.locks/{name}" for name in sorted(os.listdir(folder))]


def _titles(project, timeout):
    """The id of each ticket in the project, open or done, by its exact title."""
    try:
        tasks = json.loads(_backlog(LIST, project, timeout).stdout)["tasks"]
        return {task["title"]: task["id"] for task in tasks}
    except (ValueError, KeyError, TypeError):
        raise Refusal(
            "the project's tickets could not be listed (backlog task list --json"
            " did not print what was expected), so --skip-existing cannot be relied on"
        ) from None


def _save(path, records):
    """Write the results file whole, through a file beside it that then takes its name."""
    if not path:
        return
    partial = f"{path}.partial-{os.getpid()}"
    try:
        with open(partial, "w", encoding="utf-8") as file:
            file.write(dump_results([records[index] for index in sorted(records)]))
        os.replace(partial, path)
    finally:
        if os.path.exists(partial):
            os.remove(partial)


def _file(ticket, project, timeout):
    """File one ticket and check it. Returns (its id or None, what went wrong or None)."""
    id = None
    try:
        done = _backlog(create_command(ticket), project, timeout)
        if done.returncode != 0:
            return None, f"backlog said: {_said(done)}"
        id = created_id(done.stdout)
        if id is None:
            return None, (
                "backlog did not say which ticket it created;"
                " look for it in the project before filing again"
            )
        for number, (author, text) in enumerate(ticket.comments, 1):
            done = _backlog(comment_command(id, author, text), project, timeout)
            if done.returncode != 0:
                return id, f"comment {number} was not added: backlog said: {_said(done)}"
        try:
            viewed = json.loads(_backlog(view_command(id), project, timeout).stdout)["task"]
        except (ValueError, KeyError, TypeError):
            return id, "it could not be read back to check it"
    except subprocess.TimeoutExpired:
        return id, f"{STALLED} within {timeout:g} seconds"
    wrong = mismatches(ticket, viewed)
    return id, "; ".join(wrong) if wrong else None


def _said(done):
    """The first line of what a failed `backlog` run printed."""
    lines = (done.stderr + "\n" + done.stdout).strip().splitlines()
    return lines[0].strip() if lines else f"nothing, and exited {done.returncode}"


def _backlog(command, project, timeout):
    """Run one `backlog` command in the project folder. Never through a shell.
    Raises subprocess.TimeoutExpired, having killed it, if it runs over `timeout`."""
    return subprocess.run(
        command,
        cwd=project,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
    )


def _parser():
    parser = argparse.ArgumentParser(
        prog="file-tickets",
        description="File tickets into a Backlog project from a JSON list, and check that"
        " each arrived unchanged.",
    )
    parser.add_argument("tickets", metavar="TICKETS.json", help="the tickets file: a JSON list")
    parser.add_argument(
        "--project", required=True, metavar="DIR", help="the folder of the Backlog project"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print each backlog command and run nothing"
    )
    parser.add_argument(
        "--results", metavar="FILE", help="record each ticket's id and outcome here, to resume"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="skip a ticket whose exact title is already in the project",
    )
    parser.add_argument(
        "--ignore-locks", action="store_true", help="start even if Backlog left a lock behind"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120,
        metavar="SECONDS",
        help="how long backlog may take over one command (default 120)",
    )
    return parser
