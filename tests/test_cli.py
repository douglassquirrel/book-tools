import argparse

import pytest

from booktools import cli

pytestmark = pytest.mark.tier1


def run(body):
    return cli.run("some-command", argparse.ArgumentParser(prog="some-command"), body, [])


def test_a_file_the_system_refuses_is_one_line_and_exit_1_not_a_traceback(capsys):
    def body(args):
        raise PermissionError(13, "Permission denied", "/books/out/copy.docx")

    assert run(body) == 1
    assert capsys.readouterr().err.splitlines() == [
        "some-command: stopped by the system: Permission denied: /books/out/copy.docx"
    ]


def test_a_refusal_by_the_system_that_names_no_file_is_still_one_line(capsys):
    def body(args):
        raise OSError(28, "No space left on device")

    assert run(body) == 1
    assert capsys.readouterr().err.splitlines() == [
        "some-command: stopped by the system: No space left on device"
    ]
