import pytest

from booktools.notemap import map_lines, map_markdown, map_rows
from booktools.notes import Note
from booktools.registry import Entry, Registry

pytestmark = pytest.mark.tier1

NOTES = [
    Note("endnote", 1, "Recorded by Trinity House in the station log.", "S1.", "Chapter 1", 1),
    Note("endnote", 2, "Ibid.", "S2.", "Chapter 2", 1),
    Note("endnote", 3, "First paragraph | with a bar.\nSecond paragraph.", "S3.", "", 2),
    Note("footnote", 1, "Imperial pints.", "S4.", "Chapter 1", None),
]
IDS = {"endnote:1": "N-0001", "endnote:2": "N-0004", "endnote:3": "N-0002", "footnote:1": "N-0003"}
REGISTRY = Registry(
    [
        Entry("N-0001", "endnote", "", "", label="Trinity House"),
        Entry("N-0004", "endnote", "", ""),
        Entry("N-0002", "endnote", "", ""),
        Entry("N-0003", "footnote", "", ""),
        Entry("N-0005", "endnote", "", "", retired_in="save-2"),
    ],
    6,
)
ROWS = [
    ("N-0001", "Trinity House", "endnote:1", "1", "Chapter 1"),
    ("N-0004", "Ibid.", "endnote:2", "1", "Chapter 2"),
    ("N-0002", "First paragraph | with a bar. Second par", "endnote:3", "2", ""),
    ("N-0003", "Imperial pints.", "footnote:1", "", "Chapter 1"),
]


def test_each_row_has_the_id_a_label_both_numbers_and_the_heading():
    assert map_rows(NOTES, IDS, REGISTRY) == ROWS


def test_the_terminal_map_has_one_line_per_note_then_the_retired_ids():
    assert map_lines(ROWS, ["N-0005"]) == [
        "N-0001 | endnote:1 | Chapter 1, note 1 | Trinity House",
        "N-0004 | endnote:2 | Chapter 2, note 1 | Ibid.",
        "N-0002 | endnote:3 | note 2 | First paragraph | with a bar. Second par",
        "N-0003 | footnote:1 | Chapter 1, numbered by page | Imperial pints.",
        "retired: N-0005",
    ]
    assert map_lines(ROWS[:1], []) == ["N-0001 | endnote:1 | Chapter 1, note 1 | Trinity House"]


def test_the_markdown_map_is_a_table_and_says_where_it_came_from():
    assert map_markdown(ROWS, ["N-0005", "N-0009"], "Book.docx", "abcdef0123456789" + "0" * 48) == (
        "# Note map\n"
        "\n"
        "Made by note-map from `Book.docx` (SHA-256 `abcdef0123456789`). It is made afresh at"
        " every run: do not edit it.\n"
        "\n"
        "| ID | Label | Note | Number in the book | Under |\n"
        "|---|---|---|---|---|\n"
        "| N-0001 | Trinity House | endnote:1 | 1 | Chapter 1 |\n"
        "| N-0004 | Ibid. | endnote:2 | 1 | Chapter 2 |\n"
        "| N-0002 | First paragraph \\| with a bar. Second par | endnote:3 | 2 |  |\n"
        "| N-0003 | Imperial pints. | footnote:1 |  | Chapter 1 |\n"
        "\n"
        "Retired: N-0005, N-0009.\n"
    )
    assert map_markdown([], [], "Book.docx", "ab" * 32).endswith(
        "|---|---|---|---|---|\n\nRetired: none.\n"
    )
