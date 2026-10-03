# book-tools

A small kit of command-line programs for an author writing a non-fiction book in Microsoft
Word, with an AI assistant doing the checking and record-keeping and
[Backlog.md](https://github.com/MrLesk/Backlog.md) as the issue tracker. It is not tied to any
one book or publisher.

**Status: two commands of six work.** `propose-edits` and `file-tickets` are built and
tested; the other four are not written yet. This README will be replaced by full
instructions when all six exist.

## Using `propose-edits` now

It needs only the Python 3 that comes with Apple's command line tools. From this folder:

    ./propose-edits EDITS.json --in MANUSCRIPT.docx --out COPY.docx --dry-run
    ./propose-edits EDITS.json --in MANUSCRIPT.docx --out COPY.docx

The manuscript is only read. The second command writes `COPY.docx`, a copy holding each
edit as a tracked change for the author to accept or reject in Word, and refuses if a file
of that name exists (`--force` to replace it). `--dry-run` shows where each edit falls and
writes nothing. `./propose-edits --help` lists the other flags.

An edits file is a JSON list. Each edit gives the existing text (`find`, within one
paragraph) and what it should become (`replace`; empty to delete):

```json
[
  {"id": "E1", "find": "keeper isn’t one", "replace": "keeper is not one", "why": "no contractions"},
  {"id": "E3", "where": "endnote:1", "find": "Trinity House", "replace": "Trinity House, London"}
]
```

`where` is `body` (the default), `endnote:N` or `footnote:N` (N counts the notes through the
document from 1), or `all`. If the text occurs more than once, add `"occurrence": 2`.

Try it on the sample documents (`tests/fixtures/`):

    ./propose-edits tests/fixtures/edits.json --in tests/fixtures/sample.docx --out /tmp/x.docx

```
E1 | body, paragraph 3 | … at dusk, and the keeper [isn’t → is not] one to waste oil. | no contractions | PASS
E2 | body, paragraph 4 | … wrote every figure in a [large  →]ledger. | cut | PASS
E3 | Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London] in the station log. | place | PASS
reject all: PASS: every paragraph reads as in the original
accept all: PASS: the original with exactly the 3 edits made
revisions: PASS: 4 revisions for 3 edits, all by Claude at 2026-10-03T16:35:00Z
package: PASS: 2 parts changed, each well-formed; everything else byte-identical
wrote /tmp/x.docx
```

Each edit has a line: its id, where it is, the words around it with the change in brackets,
its reason, and PASS. The last four results are checks the command always makes on the copy
it wrote: with its changes rejected the text is the original; with them accepted it is the
original plus exactly the listed edits; every change carries the author and date; and
nothing else in the file differs by a byte. If any check fails, no copy is kept and the exit
code is 1.

An edit is refused, and nothing is written, when its text is not found, is found more than
once without `occurrence`, overlaps another edit, runs across two paragraphs, crosses a
note marker, tab, line break, picture or the edge of a link, or touches a change someone
has already tracked.

## Using `file-tickets` now

It needs [Backlog.md](https://github.com/MrLesk/Backlog.md), which is yours to install
(`brew install backlog-md`, or `npm i -g backlog.md`; tested with version 1.53.0), and a
folder where `backlog init` has been run.

    ./file-tickets TICKETS.json --project FOLDER --dry-run
    ./file-tickets TICKETS.json --project FOLDER --results results.json

A tickets file is a JSON list; only `title` is required:

```json
[
  {
    "title": "Ch. 3: Table 3.1 row 4 cites the 2019 figure",
    "description": "**Book now says:** …",
    "priority": "medium",
    "labels": ["ch3", "fact-check"],
    "milestone": "First feedback",
    "status": "To Do",
    "comments": [{"author": "Claude", "text": "Source: …"}]
  }
]
```

Each ticket is created, its comments added, and then read back and compared with what was
sent, so that text mangled on the way is caught. Every character reaches Backlog untouched
(quotes, backticks and dollar signs included), because nothing goes through a shell. One
line is printed per ticket:

```
TASK-1  filed  Ch. 3: a "quoted" `tick` $HOME title
TASK-2  filed  -5 degrees: a title starting with a dash
-  FAILED  Bad status (backlog said: Invalid status: Nonsense. Valid statuses are: To Do, In Progress, Done)
2 filed, 1 failed, 0 skipped
```

With `--results`, each ticket's id and outcome is recorded as the batch goes; running the
same command again finishes an interrupted batch without filing anything twice.
`--skip-existing` skips a ticket whose exact title is already in the project.
`./file-tickets --help` lists the other flags.

## What it will do

| Command | Job |
|---|---|
| `propose-edits` | Write a copy of a `.docx` with a list of edits in it as real tracked changes, one per edit, and verify the copy, so the author can accept or reject each in Word; the original is only read |
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

## Licence

MIT. See [LICENSE](LICENSE).
