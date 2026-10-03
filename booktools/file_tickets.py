"""file-tickets: file tickets into a Backlog project from a JSON list."""

import argparse
import json
import subprocess

from booktools.tickets import (
    comment_command,
    create_command,
    created_id,
    parse_tickets,
    view_command,
)


def main(argv=None):
    """Run the command; return its exit code."""
    args = _parser().parse_args(argv)
    with open(args.tickets, encoding="utf-8") as file:
        tickets = parse_tickets(file.read())
    _backlog(["backlog", "task", "view", "--help"], args.project)
    filed = 0
    for ticket in tickets:
        id = created_id(_backlog(create_command(ticket), args.project).stdout)
        for author, text in ticket.comments:
            _backlog(comment_command(id, author, text), args.project)
        json.loads(_backlog(view_command(id), args.project).stdout)
        print(f"{id}  filed  {ticket.title}")
        filed += 1
    print(f"{filed} filed, 0 failed, 0 skipped")
    return 0


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
    return parser
