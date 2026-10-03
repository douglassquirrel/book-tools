# book-tools

A small kit of command-line programs for an author writing a non-fiction book in Microsoft
Word, with an AI assistant doing the checking and record-keeping and
[Backlog.md](https://github.com/MrLesk/Backlog.md) as the issue tracker. It is not tied to any
one book or publisher.

**Status: just started. None of the commands exists yet.** This README describes what is
planned and will be replaced by full instructions as each command is built.

## What it will do

| Command | Job |
|---|---|
| `track-changes` | Apply a list of edits to a `.docx` as real tracked changes, one per edit, and verify the result, so the author can accept or reject each in Word |
| `file-tickets` | File tickets into a Backlog project from a JSON list, with every character of the text arriving unchanged |
| `note-map` | Give every footnote and endnote a permanent ID and keep a map to its current number, so Word can renumber freely and your records never need renumbering |
| `compare-saves` | Say what changed between two saves of a manuscript: words, formatting and structure |
| `check-spacing` | List the paragraphs that are not at the expected line spacing, following Word's style inheritance |
| `sources-to-text` | Turn a folder of source PDFs into searchable text with page markers, using OCR where a page has no text |

Each command does one job and takes every path as an argument. None of them writes over the
file it was given: the manuscript is only ever read, and a command that produces a document
writes a new one.

## What it will need

- macOS, with the Python 3 that comes with Apple's command line tools (3.9 or later). No Python
  packages to install.
- From [Homebrew](https://brew.sh), each needed only by the command named:
  - `pandoc` (`compare-saves`)
  - `poppler` and `tesseract` (`sources-to-text`)
  - `backlog-md` (`file-tickets`). Backlog is yours to install; the kit never installs or
    configures it.

## Contributing

Development is test-first: every piece of behaviour starts as a failing test. The tests use
only small invented documents; no real manuscript, source or ticket is ever committed here.
