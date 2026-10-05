"""pandoc's reading of a .docx as markdown: what the assistant reads and what is diffed."""

import subprocess

PANDOC = ["pandoc", "-f", "docx", "-t", "markdown-smart", "--wrap=none"]
INSTALL = (
    "Install it with `brew install pandoc`, or on a Mac without Homebrew with the"
    " installer package from pandoc.org"
)


class NoMarkdown(Exception):
    """pandoc could not give the text of a save."""


def markdown(path, timeout):
    """The text of a .docx as pandoc reads it."""
    try:
        done = subprocess.run(
            PANDOC + [path], stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise NoMarkdown(
            f"pandoc did not finish with {path} within {timeout:g} seconds"
        ) from None
    if done.returncode != 0:
        said = done.stderr.decode("utf-8", "replace").strip().splitlines()
        raise NoMarkdown(f"pandoc failed on {path}: {said[0] if said else done.returncode}")
    if not done.stdout:
        raise NoMarkdown(f"pandoc printed nothing for {path}")
    try:
        return done.stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise NoMarkdown(f"pandoc did not print text for {path}") from None
