import json
from pathlib import Path

import pytest

from tests.fixtures.make_fixtures import build

pytestmark = pytest.mark.tier2

FIXTURES = Path(__file__).parent / "fixtures"
NAMES = ["edits.json", "sample-edited.docx", "sample.docx"]


def test_the_committed_samples_are_exactly_what_their_generator_makes(tmp_path):
    build(tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == NAMES
    for name in NAMES:
        assert (FIXTURES / name).read_bytes() == (tmp_path / name).read_bytes(), name


def test_the_sample_edits_file_holds_three_edits():
    assert len(json.loads((FIXTURES / "edits.json").read_text(encoding="utf-8"))) == 3
