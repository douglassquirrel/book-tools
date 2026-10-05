import pytest

from booktools.extract import ExtractError, reading_text

pytestmark = pytest.mark.tier1

MARKDOWN = (
    "## Chapter 1\n\n"
    "The lamp was lit.[^1] She wrote it down.[^2]\n\n"
    "## Chapter 2\n\n"
    "The log is missing.[^3] A bracket \\[^2\\] typed by hand is left alone.\n\n"
    "[^1]: Recorded in the log.\n\n"
    "[^2]: Imperial pints.\n\n"
    "    A second paragraph of the same note.\n\n"
    "[^3]: Ibid.\n"
)
# pandoc counts endnotes and footnotes in one sequence, as their markers come.
ORDER = [
    ("N-0001", "Chapter 1, note 1"),
    ("N-0003", "Chapter 1, note 1"),
    ("N-0002", "note 2"),
]
SAVE = "abcdef0123456789" + "0" * 48


def test_puts_the_permanent_id_at_each_marker_and_note_with_the_number_the_book_prints():
    assert reading_text(MARKDOWN, ORDER, "Book.docx", SAVE) == (
        "<!-- Made by note-map from `Book.docx` (SHA-256 `abcdef0123456789`), for reading"
        " only: each note is named by its permanent ID. Do not edit it. -->\n\n"
        "## Chapter 1\n\n"
        "The lamp was lit.[^N-0001] She wrote it down.[^N-0003]\n\n"
        "## Chapter 2\n\n"
        "The log is missing.[^N-0002] A bracket \\[^2\\] typed by hand is left alone.\n\n"
        "[^N-0001]: <!-- Chapter 1, note 1 --> Recorded in the log.\n\n"
        "[^N-0003]: <!-- Chapter 1, note 1 --> Imperial pints.\n\n"
        "    A second paragraph of the same note.\n\n"
        "[^N-0002]: <!-- note 2 --> Ibid.\n"
    )


def test_a_text_with_no_notes_gets_only_its_header():
    assert reading_text("Only words.\n", [], "Book.docx", SAVE).endswith("-->\n\nOnly words.\n")


@pytest.mark.parametrize(
    "markdown, said",
    [
        (
            "One.[^1]\n\n[^1]: A note.\n",
            "pandoc read 1 note where the manuscript has 3",
        ),
        (
            MARKDOWN + "\n[^4]: One more.\n",
            "pandoc read 4 notes where the manuscript has 3",
        ),
        (
            MARKDOWN.replace("down.[^2]", "down.[^7]"),
            "pandoc's text has a marker [^7] and only 3 notes",
        ),
    ],
)
def test_a_text_whose_notes_do_not_tally_with_the_manuscript_is_refused(markdown, said):
    with pytest.raises(ExtractError) as raised:
        reading_text(markdown, ORDER, "Book.docx", SAVE)
    assert str(raised.value) == said
