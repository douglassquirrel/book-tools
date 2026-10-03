"""file-tickets: file tickets into a Backlog project from a JSON list."""

import argparse
import json
import os
import shlex
import shutil
import subprocess

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


def main(argv=None):
    """Run the command; return its exit code."""
    return cli.run("file-tickets", _parser(), _run, argv)


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
    if "--json" not in _backlog(["backlog", "task", "view", "--help"], args.project).stdout:
        raise Refusal(
            "this backlog has no `task view --json`, which is needed to check each"
            f" ticket; the kit was tested with Backlog {TESTED_WITH}"
        )
    filed = failed = skipped = 0
    for ticket in tickets:
        earlier = records.get(ticket.index)
        if earlier and earlier["id"]:
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
        id, fault = _file(ticket, args.project)
        if fault:
            failed += 1
            print(f"{id or '-'}  FAILED  {ticket.title} ({fault})")
        else:
            filed += 1
            print(f"{id}  filed  {ticket.title}")
        records[ticket.index] = {
            "index": ticket.index,
            "title": ticket.title,
            "id": id,
            "outcome": f"failed: {fault}" if fault else "filed",
        }
        _save(args.results, records)
    print(f"{filed} filed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


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


def _file(ticket, project):
    """File one ticket and check it. Returns (its id or None, what went wrong or None)."""
    done = _backlog(create_command(ticket), project)
    if done.returncode != 0:
        return None, f"backlog said: {_said(done)}"
    id = created_id(done.stdout)
    if id is None:
        return None, (
            "backlog did not say which ticket it created;"
            " look for it in the project before filing again"
        )
    for number, (author, text) in enumerate(ticket.comments, 1):
        done = _backlog(comment_command(id, author, text), project)
        if done.returncode != 0:
            return id, f"comment {number} was not added: backlog said: {_said(done)}"
    try:
        viewed = json.loads(_backlog(view_command(id), project).stdout)["task"]
    except (ValueError, KeyError, TypeError):
        return id, "it could not be read back to check it"
    wrong = mismatches(ticket, viewed)
    return id, "; ".join(wrong) if wrong else None


def _said(done):
    """The first line of what a failed `backlog` run printed."""
    lines = (done.stderr + "\n" + done.stdout).strip().splitlines()
    return lines[0].strip() if lines else f"nothing, and exited {done.returncode}"


def _backlog(command, project):
    """Run one `backlog` command in the project folder. Never through a shell."""
    return subprocess.run(
        command,
        cwd=project,
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
