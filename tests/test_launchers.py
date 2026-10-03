import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.docxkit import pack_docx
from tests.samples import SAMPLE_EDITS, sample_parts

pytestmark = pytest.mark.tier2

KIT = Path(__file__).resolve().parent.parent


@pytest.fixture
def kit(tmp_path):
    """A copy of the kit's code in a folder of its own, so that what running it
    leaves behind can be seen."""
    copy = tmp_path / "kit"
    copy.mkdir()
    shutil.copytree(KIT / "booktools", copy / "booktools", ignore=shutil.ignore_patterns("__pycache__"))
    for launcher in ("propose-edits",):
        shutil.copy2(KIT / launcher, copy / launcher)
    return copy


def run(kit, command, *args, cwd):
    env = {"PATH": os.environ["PATH"]}
    return subprocess.run(
        [sys.executable, str(kit / command), *args],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=60,
    )


def test_propose_edits_runs_from_another_folder_and_leaves_no_bytecode_anywhere(kit, tmp_path):
    book = tmp_path / "book"
    book.mkdir()
    pack_docx(book / "in.docx", sample_parts())
    (book / "edits.json").write_text(json.dumps(SAMPLE_EDITS), encoding="utf-8")
    done = run(kit, "propose-edits", "edits.json", "--in", "in.docx", "--out", "new.docx", cwd=book)
    assert (done.returncode, done.stderr) == (0, "")
    assert done.stdout.splitlines()[-1] == "wrote new.docx"
    assert sorted(path.name for path in book.iterdir()) == ["edits.json", "in.docx", "new.docx"]
    assert list(kit.rglob("__pycache__")) == []


def test_the_launcher_is_executable_and_asks_for_python3_on_the_path():
    launcher = KIT / "propose-edits"
    assert os.access(launcher, os.X_OK)
    assert launcher.read_text().splitlines()[0] == "#!/usr/bin/env python3"


def test_help_names_every_flag_in_the_synopsis(kit, tmp_path):
    done = run(kit, "propose-edits", "--help", cwd=tmp_path)
    assert done.returncode == 0
    for flag in (
        "EDITS.json", "--in", "--out", "--author", "--date", "--dry-run", "--force",
        "--keep-on-failure", "--utc", "--tmp", "--timeout",
    ):
        assert flag in done.stdout
