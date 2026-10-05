"""What every command does the same way: exit codes, refusals and interruption."""

import os
import sys


class Refusal(Exception):
    """The command will not start. `lines` say why, the first being the headline."""

    def __init__(self, *lines):
        super().__init__(lines[0])
        self.lines = lines


def run(name, parser, body, argv, interrupted="interrupted"):
    """Parse `argv` and run `body(args)`, returning the exit code: what `body`
    returns, 2 for a usage error or a Refusal, 130 when interrupted, and 1 when the
    system refuses the command a file (no permission, no room): said in one line,
    never a traceback."""
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return stop.code
    try:
        return body(args)
    except KeyboardInterrupt:
        print(f"{name}: {interrupted}", file=sys.stderr)
        return 130
    except Refusal as refusal:
        print(f"{name}: {refusal.lines[0]}", file=sys.stderr)
        for line in refusal.lines[1:]:
            print(f"  {line}", file=sys.stderr)
        return 2
    except OSError as error:
        said = error.strerror or str(error)
        where = f": {error.filename}" if error.filename else ""
        print(f"{name}: stopped by the system: {said}{where}", file=sys.stderr)
        return 1


def remove(command, path, what, shown=None, folder=False):
    """Remove a file (or an empty folder) that the command itself made. Where the
    system will not allow it, say so in one line and return False: that is something
    for the user to clear away by hand, never a reason to stop with a traceback."""
    try:
        (os.rmdir if folder else os.remove)(path)
    except OSError as error:
        reason = error.strerror or str(error)
        print(
            f"{command}: could not remove {what} {shown or path}: {reason}; remove it by hand",
            file=sys.stderr,
        )
        return False
    return True
