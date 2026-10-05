# book-tools

A small kit of command-line programs for an author writing a non-fiction book in Microsoft
Word, with an AI assistant doing the checking and record-keeping and
[Backlog.md](https://github.com/MrLesk/Backlog.md) as the issue tracker. It is not tied to any
one book or publisher. Each command does one job, takes every path as an argument, and never
writes over the file it was given: the manuscript is only ever read.

| Command | Job |
|---|---|
| `propose-edits` | Write a **copy** of a `.docx` with a list of edits in it as tracked changes, one per edit, and verify the copy, so the author can accept or reject each in Word |
| `file-tickets` | File tickets into a Backlog project from a JSON list, with every character arriving unchanged, and check each one |
| `note-map` | Give every endnote and footnote a permanent ID and keep a map to its current number, so Word can renumber freely and your records never need renumbering; and write a reading text of the manuscript with those IDs in it |
| `compare-saves` | Say what changed between two saves of a manuscript: structure, words and formatting |
| `check-spacing` | List the paragraphs that are not at the expected line spacing, following Word's style inheritance |
| `sources-to-text` | Turn a folder of source PDFs into searchable text with page markers, using OCR where a page has no text |

## Requirements

- **macOS** (built and tested on macOS 26.6), with the **Python 3** that comes with Apple's
  command line tools (3.9 or later). No Python packages are needed.
- From [Homebrew](https://brew.sh), each needed only by the command named:
  - `pandoc`: `compare-saves` (its text diff), `note-map --extract` (the reading text) and
    `sources-to-text` (for `.epub` files). On a
    Mac without Homebrew, use the installer package from [pandoc.org](https://pandoc.org).
  - `poppler` (which provides `pdftotext` and `pdftoppm`) and `tesseract`: `sources-to-text`
    (for `.pdf` files).
  - `git`: only for `compare-saves --git`. It comes with Apple's command line tools.
- **Backlog, which is yours to install**: `brew install backlog-md` (or `npm i -g backlog.md`).
  Needed by `file-tickets` only. The kit never installs, updates or configures Backlog.
  Tested with Backlog 1.53.0.
- **Pillow, optional**: `brew install pillow` (Homebrew's Python refuses `pip install`; for
  a Python that is not Homebrew's, `python3 -m pip install --user Pillow`). With it, `sources-to-text`
  notices a page scanned sideways or upside down; without it each page is read as it stands
  and the command says so.

A command that needs a program you have not installed refuses to start and tells you what
to install.

## Installation

    brew install pandoc poppler tesseract backlog-md     # pandoc: compare-saves, note-map --extract; poppler+tesseract: sources-to-text; backlog: file-tickets
    git clone https://github.com/douglassquirrel/book-tools.git ~/projects/book-tools && cd ~/projects/book-tools
    ./propose-edits --help

The six commands are the files of those names in the repository's folder. Run them from
there, give their full path, or link them into a folder on your `PATH`.

## Quick start

The repository holds two small invented documents, `tests/fixtures/sample.docx` and a later
save of it, `sample-edited.docx`, and an edits file. See where three edits would fall,
without writing anything:

    ./propose-edits tests/fixtures/edits.json --in tests/fixtures/sample.docx --out /tmp/x.docx --dry-run

```
E1 | body, paragraph 3 | … at dusk, and the keeper [isn’t → is not] one to waste oil. | no contractions | found
E2 | body, paragraph 4 | … wrote every figure in a [large  →]ledger. | cut | found
E3 | Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London] in the station log. | place | found
dry run: 3 edits found; /tmp/x.docx would be written; nothing written
```

See what changed between the two saves:

    ./compare-saves tests/fixtures/sample.docx tests/fixtures/sample-edited.docx

```
old: tests/fixtures/sample.docx
new: tests/fixtures/sample-edited.docx

== Structure and counts (old | new)
sha256: da8722ca2c1c48b4 | a72c511b3668338d
revision: 3 | 4
modified (London time): 2026-10-01 10:00 | 2026-10-02 18:30
parts that differ: word/document.xml, word/endnotes.xml, docProps/core.xml
media: the same 1 file
paragraphs: 9 | 10 (+1)
tracked changes: 0 | 0
trackRevisions: off | off
comments: 0 | 0
endnote markers: 2 | 3 (+1)
endnotes: 2 | 3 (+1)
footnote markers: 1 | 1
footnotes: 1 | 1
straight quotes: 0 | 0
links in notes: 0 | 0
highlighted runs: 0 | 0
notes of more than one paragraph: none | none

== Paragraph by paragraph
===== word/document.xml paragraphs 9 10
TEXT 2: insert 'The lamp was lit at dusk,' -> '{endnoteReference}The lamp was lit at dawn,'
TEXT 2: replace 'The lamp was lit at dusk, and the keeper isn’t on' -> 'nce}The lamp was lit at dawn, and the keeper isn’t on'
FORMAT 3: 5 chars, e.g. at 'e every figure in a large ledger.{footno': old[b] new[]
FORMAT 5: 30 chars, e.g. at 'A caption set in ano': old[font=Times-Roman] new[]
PARA-PROPS 6: 'A line at exact spacing.'
   old <w:pPr><w:spacing w:line="280" w:lineRule="exact"/></w:pPr>
   new <w:pPr><w:spacing w:line="300" w:lineRule="exact"/></w:pPr>
ADDED 7: 'A paragraph added in the later save.'
differing paragraphs 5
===== word/endnotes.xml paragraphs 4 5
ADDED 2: ' A note added in the later save.'
differing paragraphs 1
===== word/footnotes.xml paragraphs 3 3
differing paragraphs 0

== Text diff (body and notes, as pandoc reads them)
=== BODY replace
  OLD: The lamp was lit at dusk, and the keeper isn’t one to waste oil.[^1]
  OLD: She wrote *every* figure in a **large** ledger.[^2]
  NEW: [^1]The lamp was lit at dawn, and the keeper isn’t one to waste oil.[^2]
  NEW: She wrote *every* figure in a large ledger.[^3]
=== BODY insert
  NEW: A paragraph added in the later save.
=== NOTES insert old [] new [1]
  NEW: A note added in the later save.
```

## Usage

Every command has `--help`. Results and progress go to standard output and errors to
standard error. Times are London time unless `--utc` is given.

### `propose-edits`: a copy of a `.docx` with edits as tracked changes

    propose-edits EDITS.json --in MANUSCRIPT.docx --out COPY.docx [--registry FILE]
                  [--author NAME] [--date ISO] [--dry-run] [--force] [--keep-on-failure]
                  [--utc] [--tmp DIR] [--timeout SECONDS]

The manuscript is read and never changed. The command writes `COPY.docx`, a copy in which
each edit is a real tracked change (author, date and id) for the author to accept or reject
in Word. Only the words that change are marked, as whole words: "isn’t" struck out and
"is not" inserted, not a few letters inside a word. The new words take the formatting of the
text they replace.

**The edits file** is a JSON list. A complete example (this is `tests/fixtures/edits.json`):

```json
[
  {
    "id": "E1",
    "find": "keeper isn’t one",
    "replace": "keeper is not one",
    "why": "no contractions"
  },
  {
    "id": "E2",
    "find": "large ledger",
    "replace": "ledger",
    "why": "cut"
  },
  {
    "id": "E3",
    "where": "endnote:1",
    "find": "Trinity House",
    "replace": "Trinity House, London",
    "why": "place"
  }
]
```

| Key | Meaning |
|---|---|
| `find` | The existing text, exactly, within one paragraph. It is found even where Word has split it across runs. Required. |
| `replace` | What it should become; an empty string deletes it. To insert words, give the neighbouring text in `find` and the same text plus the new words in `replace`. Required. |
| `where` | `body` (the default), `endnote:N` or `footnote:N`, `all`, or a note's permanent ID as `note-map` gave it (`N-0042`). N counts the notes of that kind through the document from 1, whatever number the book prints; it moves whenever a note is added or removed, and the ID does not (see "Naming a note by its permanent ID" below). |
| `occurrence` | Which match to use, from 1, when the text occurs more than once in the place searched. |
| `id` | Your name for the edit, shown in the report. |
| `why` | The reason, shown in the report only. Nothing is written into the document as a comment. |

Applying the three sample edits:

    ./propose-edits tests/fixtures/edits.json --in tests/fixtures/sample.docx --out /tmp/x.docx

```
E1 | body, paragraph 3 | … at dusk, and the keeper [isn’t → is not] one to waste oil. | no contractions | PASS
E2 | body, paragraph 4 | … wrote every figure in a [large  →]ledger. | cut | PASS
E3 | Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London] in the station log. | place | PASS
reject all: PASS: every paragraph reads as in the original
accept all: PASS: the original with exactly the 3 edits made
revisions: PASS: 4 revisions for 3 edits, all by Claude at 2026-10-03T18:18:00Z
package: PASS: 2 parts changed, each well-formed; everything else byte-identical
wrote /tmp/x.docx
```

Each edit has one line, in the order the edits fall in the document: its id, where it is
(a note is shown as the book numbers it, under its heading, with its count after), 25
characters either side of the change, the change in brackets as `[old → new]`, its reason,
and its result. This is the sheet to read beside the copy in Word.

**The four results at the end are checks the command always makes on the copy it wrote.**
They cannot be skipped.

- *reject all*: with this run's changes rejected, every paragraph reads as in the original.
- *accept all*: with them accepted, the text is the original with exactly the listed
  replacements made, and nothing else.
- *revisions*: each edit has exactly its own tracked changes, carrying this run's author
  and date; the copy holds no other new change.
- *package*: every paragraph that was not edited, and every other part of the file
  (styles, pictures, settings), is the same byte for byte, and the edited parts are
  well-formed.

**Naming a note by its permanent ID.** An edits file is often run against a later save than
the one it was written from, and by then `endnote:42` may be another note. Give `where` the
note's permanent ID instead, and the registry with `--registry`:

    ./propose-edits by-id.json --in tests/fixtures/sample-edited.docx --out /tmp/y.docx --registry notes.json --dry-run

```
E3 | N-0001 → Chapter 1, note 2 (endnote:2) | …Recorded by Trinity House[→ , London] in the station log. | place | found
dry run: 1 edit found; /tmp/y.docx would be written; nothing written
```

The command finds where that note stands in the save it was given, by the same matching
`note-map` uses, and shows it as the book numbers it now. The registry is only read, never
written. An ID the registry does not have, one that is retired, one whose note is not in
this save, and one whose note cannot be told apart without guessing (run `note-map` on the
save first and settle it there) are each an edit that cannot be placed: named with the
reason, nothing written, exit 1. An edit that names an ID when no `--registry` is given is
refused before anything is done (exit 2).

**Notes under an edit's line.** When accepting an edit would leave something at its edges
that you probably do not want, a line under it says so, in the dry run and in the report:

```
C | body, paragraph 1 | One sentence. [A second sentence. →] A third. | | found
note: accepting C leaves two spaces in a row: "…sentence.  A third."
```

The kinds are: two spaces in a row; a punctuation mark doubled; a space before a punctuation
mark; no space after one; two words run together. Only what the edit itself brings about is
noted. A note is advice: the edit is still made exactly as written, and the exit code does
not change. Put the space inside `find` (or `replace`) to cure it.

**If a check fails**, the copy is not kept, the edit at fault is marked `FAIL`, and the exit
code is 1. This means the command has a fault, not your edits file: please report it with
the edits file. `--keep-on-failure` keeps the failed copy so it can be looked at.

**An edit is refused**, with every refused edit named and nothing written (exit 1), when its
text is not found; is found more than once without `occurrence`; overlaps another edit; runs
from one paragraph into the next; crosses a note marker, tab, line break, picture, bookmark,
field, the start or end of a comment or of a hyperlink; or touches a change someone has
already tracked (accept or reject that change in Word first). An edit wholly inside a
hyperlink is fine.

| Flag | Meaning |
|---|---|
| `--in FILE` | The manuscript. Only read. |
| `--out FILE` | The copy to write. Refused if it exists, unless `--force`; refused always if it is the manuscript or the registry. |
| `--registry FILE` | `note-map`'s registry. Needed when an edit's `where` is a permanent ID; only read. |
| `--author NAME` | The author on the changes (default `Claude`). |
| `--date ISO` | The date and time on the changes (default: now). `2026-10-03T14:46` is London time; with an offset or `Z` it is that moment. |
| `--utc` | Write the date in UTC. |
| `--dry-run` | Show where each edit falls and write nothing. |
| `--force` | Replace an existing `--out`. |
| `--keep-on-failure` | Keep the copy even if a check fails. |
| `--tmp DIR` | Where to make the scratch folder. |
| `--timeout SECONDS` | Accepted for uniformity; this command runs no other program. |

A document that already holds tracked changes is accepted: `find` is matched against the
text as it reads with those changes accepted, and the checks cover only this run's changes.

### `file-tickets`: tickets into Backlog from JSON

    file-tickets TICKETS.json --project DIR [--dry-run] [--results FILE] [--skip-existing]
                 [--ignore-locks] [--timeout SECONDS]

`DIR` is a folder where `backlog init` has been run. **The tickets file** is a JSON list;
only `title` is required. A complete example:

```json
[
  {
    "title": "Ch. 3: Table 3.1 row 4 cites the 2019 figure, source says 2021",
    "description": "## Current state\n\n**Book now says:** …",
    "priority": "medium",
    "labels": ["ch3", "fact-check"],
    "milestone": "First feedback",
    "status": "To Do",
    "comments": [{"author": "Claude", "text": "Source: …"}]
  },
  {"title": "Only a title"}
]
```

`priority` is `high`, `medium` or `low`. A title must be on one line; a label may not hold a
comma.

For each ticket, in order, the command runs `backlog task create`, then adds each comment,
then reads the ticket back with `backlog task view --json` and compares it with what was
sent. Nothing passes through a shell, so quotes, backticks and dollar signs arrive
untouched. Backlog itself trims a description, turns CRLF into LF and several blank lines
into one; the comparison allows for exactly that and nothing more. One line is printed per
ticket (this run was against Backlog 1.53.0 in a throwaway project):

```
TASK-1  filed  Ch. 3: a "quoted" `tick` $HOME title
TASK-2  filed  -5 degrees: a title starting with a dash
-  FAILED  Bad status (backlog said: Invalid status: Nonsense. Valid statuses are: To Do, In Progress, Done)
2 filed, 1 failed, 0 skipped
```

A ticket that fails does not stop the batch; the exit code is 1 if any failed.

| Flag | Meaning |
|---|---|
| `--project DIR` | The Backlog project's folder. |
| `--results FILE` | Record each ticket's position, title, id and outcome here, after every ticket. If the file exists it is read first: tickets already filed are skipped (`already filed`), so an interrupted batch can be finished by running the same command again without filing anything twice. A ticket that was created but could not be confirmed is never created again; it is reported until you put it right by hand. A results file that belongs to another tickets file is refused. |
| `--skip-existing` | Skip a ticket whose exact title is already in the project, open or done. |
| `--dry-run` | Print each `backlog` command that would run, quoted for reading, and run nothing. |
| `--ignore-locks` | Start even though Backlog has left a lock in `backlog/.locks/`. The command reports locks before and after, and never removes one. |
| `--timeout SECONDS` | How long one `backlog` command may take (default 120). If one runs over, the whole batch stops, since going on could file tickets twice or out of order. |

### `note-map`: permanent IDs for notes

    note-map MANUSCRIPT.docx --registry FILE [--map FILE] [--extract FILE [--force]]
             [--assign ID=NUMBER ...] [--dry-run] [--timeout SECONDS]

Word renumbers notes whenever one is added or removed. Name a note in your records by a
permanent ID instead, and let this command say what number it has today.

    ./note-map tests/fixtures/sample.docx --registry notes.json

```
3 notes: 0 carried, 3 new, 0 retired
new: N-0001 endnote:1 Recorded by Trinity House in the station
new: N-0002 endnote:2 Ibid.
new: N-0003 footnote:1 Imperial pints.
N-0001 | endnote:1 | Chapter 1, note 1 | Recorded by Trinity House in the station
N-0002 | endnote:2 | Chapter 2, note 2 | Ibid.
N-0003 | footnote:1 | Chapter 1, note 1 | Imperial pints.
```

After a later save, in which a note was added in front of the others:

    ./note-map tests/fixtures/sample-edited.docx --registry notes.json

```
4 notes: 3 carried, 1 new, 0 retired
new: N-0004 endnote:1 A note added in the later save.
N-0004 | endnote:1 | Chapter 1, note 1 | A note added in the later save.
N-0001 | endnote:2 | Chapter 1, note 2 | Recorded by Trinity House in the station
N-0002 | endnote:3 | Chapter 2, note 3 | Ibid.
N-0003 | footnote:1 | Chapter 1, note 1 | Imperial pints.
```

Every ID was carried although every number moved. Each map line gives the ID, the note's
count through the document, the heading it falls under with the number the book prints
(which differs from the count where notes restart in each chapter), and a label: one you
have typed into the registry's `label` field, or else the first 40 characters of the note.

A note is recognised by its text together with the sentence its marker sits in. It keeps its
ID when one of the two is exactly as recorded and the other is still recognisably the same.
A note with no match is new; a recorded note with none is **retired**: its ID stays in the
registry and is never used again.

**The command never guesses.** If a note was rewritten *and* moved, or two notes are equally
good matches, it lists each such note with its candidates and the exact flag to add, writes
nothing, and exits 1:

```
unclear: endnote:1 "The station log, as recorded by Trinity " in the sentence "At dusk the lamp was always lit; the keeper isn’t one to waste oil."
  if it is N-0001 "Recorded by Trinity House in the station": --assign N-0001=endnote:1
  if it is a new note: --assign new=endnote:1
```

**The reading text.** An assistant reads the manuscript as pandoc's markdown, in which
notes are `[^1]`, `[^2]`… in the order they come, numbers that move with every note added.
`--extract FILE` writes that same text with each note's permanent ID in place of the number,
at the marker and at the note, so that what is read already names notes as the records do:

    ./note-map tests/fixtures/sample-edited.docx --registry notes.json --extract reading.md

```
<!-- Made by note-map from `sample-edited.docx` (SHA-256 `a72c511b3668338d`), for reading only: each note is named by its permanent ID. Do not edit it. -->

# The Lighthouse Ledger

## Chapter 1

[^N-0004]The lamp was lit at dawn, and the keeper isn’t one to waste oil.[^N-0001]

She wrote *every* figure in a large ledger.[^N-0003]
…
The log for March is missing.[^N-0002]

[^N-0004]: <!-- Chapter 1, note 1 --> A note added in the later save.

[^N-0001]: <!-- Chapter 1, note 2 --> Recorded by Trinity House in the station log.

[^N-0003]: <!-- Chapter 1, note 1 --> Imperial pints.

[^N-0002]: <!-- Chapter 2, note 3 --> Ibid.
```

The comment at each note is where the book shows it: its heading and the number it prints,
for when you talk to the publisher. The first line names the save by its file name and the
first 16 characters of its SHA-256, as the map does. The text is for reading only; it is
never the manuscript. It needs pandoc, and it is written in the same run as the registry and
the map or not at all: if a note is unclear, if pandoc fails, or if pandoc counts a
different number of notes than the manuscript holds, nothing whatever is written and the
exit code is 1, so the text never carries a guessed ID.

| Flag | Meaning |
|---|---|
| `--registry FILE` | The registry (JSON), created on the first run. Keep it with your records, in git. It is rewritten whole; no backup copy is left beside it. |
| `--map FILE` | Write the map to this file as a Markdown table, made afresh at every run, instead of printing it. |
| `--assign ID=NUMBER` | Settle an unclear note: that ID is the note now numbered `endnote:N` or `footnote:N`. `--assign new=NUMBER` says it is a new note. May be given several times. |
| `--extract FILE` | Also write the reading text here (see above). Refused if the file exists, unless `--force`; refused always if it is the manuscript, the registry or the map. Needs pandoc. |
| `--force` | Replace an existing `--extract` file. |
| `--dry-run` | Report what would be carried, new and retired; write nothing. pandoc is not run. |
| `--timeout SECONDS` | How long pandoc may take to read the manuscript for `--extract` (default 120). |

### `compare-saves`: two saves of a manuscript

    compare-saves OLD.docx NEW.docx [--ignore-font NAME] [--no-text-diff] [--full-diff]
                  [--no-counts] [--utc] [--tmp DIR] [--timeout SECONDS]
    compare-saves --git OLDREV [NEWREV] FILE.docx [the same options]

The report (shown in full under Quick start) has three sections.

1. **Structure and counts**, old beside new, with the difference where a number changed.
2. **Paragraph by paragraph**, for the body, the endnotes and the footnotes. Paragraphs are
   paired by their text, so one added paragraph does not put the rest out of step.

   | Line | Meaning |
   |---|---|
   | `TEXT k: …` | The text differs; one line for each differing span, with 25 characters either side. |
   | `FORMAT k: N chars, e.g. at '…': old[…] new[…]` | The text is the same but N characters differ in formatting (bold, italic, underline, strike, caps, small caps, hidden, size, superscript, highlight, colour, character style, font). |
   | `FONT-NAME-ONLY k: …` | The same, where the *only* difference is a font name you asked to ignore with `--ignore-font`. Word sometimes changes a font's name on saving without any visible change; this line lets you set those aside. |
   | `PARA-PROPS k:` | The paragraph's own properties (style, spacing, alignment…) differ; the old and new are shown. |
   | `ADDED j: '…'` | A paragraph only the new save has, with its first 60 characters. |
   | `REMOVED i: '…'` | A paragraph only the old save has. |

   `k` is the paragraph's index, from 0. Where a paragraph's index differs between the
   saves the line says `j (old i)`.
3. **Text diff** of body and notes as pandoc reads them. A note's number changing is not
   reported as a change; a change to a note gives its old and new numbers. Each block is
   headed `=== BODY replace` (or `insert`, `delete`) or `=== NOTES replace old [2] new [3]`.

   | Line | Meaning |
   |---|---|
   | `  OLD: …` and `  NEW: …` | A paragraph or note as it was and as it is, whole. |
   | `  CHANGED: …25 characters[old → new]25 characters…` | A changed paragraph or note of more than 200 characters, shown as its changed words only, one line for each run of changed words, in place of its `OLD` and `NEW` lines. An empty side (`[→ new ]`, `[old  →]`) is words added or cut. |

   A paragraph of 200 characters or fewer, lines added or removed, a block in which the old
   and new lines are not one for one, and a paragraph so rewritten that its changed words
   would be longer than the paragraph, are printed whole. `--full-diff` prints everything
   whole.

The exit code is 0 whether or not there are differences: it is a report.

| Flag | Meaning |
|---|---|
| `--git` | Compare committed versions of one file. The old side is `FILE.docx` at `OLDREV` (a commit, a tag, `HEAD~1`); the new side is the same file at `NEWREV`, or the file on disk if `NEWREV` is left out. Only `git show` and `git log` are run; nothing in the repository is touched. |
| `--ignore-font NAME` | See `FONT-NAME-ONLY` above. May be given more than once. |
| `--no-text-diff` | Leave out section 3. pandoc is then not needed. |
| `--full-diff` | In section 3, print every changed paragraph and note whole, as `OLD` and `NEW` lines, however long. |
| `--no-counts` | Leave out section 1. |
| `--utc` | Show times in UTC. |
| `--tmp DIR` | Where to make the scratch folder (used by `--git`). |
| `--timeout SECONDS` | How long pandoc or git may take over one call (default 120). |

### `check-spacing`: paragraphs not at the expected line spacing

    check-spacing MANUSCRIPT.docx [--expect double|single|N] [-v]

Publishers ask for double spacing throughout, notes included, and Word applies spacing
through a chain of styles that cannot be seen. This follows the chain.

    ./check-spacing tests/fixtures/sample.docx -v

```
== TEXT: 9 paragraphs, 8 double, 1 not double
   by spacing: [('exact 14 pt', 1)]
   by style: [('Normal', 1)]
   TEXT p7 [Chapter 1] Normal | exact 14 pt | 'A line at exact spacing.'
== NOTES: 2 paragraphs, 2 double, 0 not double
   by spacing: []
   by style: []
== FOOTNOTES: 1 paragraphs, 1 double, 0 not double
   by spacing: []
   by style: []
```

`TEXT` is the body, `NOTES` the endnotes. With `-v` each paragraph that does not match is
listed: its number (from 1), the heading above it, its style, its spacing, `[IMG]` if it
holds a picture, and its first 90 characters. A spacing of "exactly" or "at least" so many
points never counts as matching. A paragraph with no spacing set anywhere counts as single.
The separator entries Word keeps among the notes are not counted: they are not paragraphs
of the book.

The exit code is 1 if any paragraph does not match, 0 if all do.

| Flag | Meaning |
|---|---|
| `--expect double\|single\|N` | The spacing every paragraph should have: `double` (the default), `single`, or N 240ths of a line (`360` is one and a half). A spacing within 12 of the expected value matches. |
| `-v`, `--verbose` | List each paragraph that does not match. |

### `sources-to-text`: a folder of sources to searchable text

    sources-to-text SOURCES_DIR [--out DIR] [--workers N] [--seconds S] [--min-chars 80]
                    [--dpi-scale 2800] [--no-rotate] [--redo FILE...] [--skip NAME ...]
                    [--clear-locks] [--tmp DIR] [--timeout SECONDS] [--ocr-timeout SECONDS]

Every file directly in `SOURCES_DIR` (not in its sub-folders) gets a text counterpart,
`NAME.txt`, in the output folder, smallest file first. A file that already has one is left
alone.

    ./sources-to-text sources

```
talk.mp4: skipped (not a kind this command converts)
notes.md: copied
ledger.pdf: 1 pages, 0 read by OCR, 0 turned
2 converted, 1 skipped, 0 failed
```

- **`.pdf`**: the text of each page under a header, in exactly one of these forms:

  ```
  === PDF page 3 of 12 ===
  === PDF page 3 of 12 (OCR) ===
  === PDF page 3 of 12 (OCR, page turned 90° clockwise) ===
  ```

  A page with fewer than `--min-chars` characters (spaces aside) is rendered and read by
  OCR. If Pillow is installed, a page that reads poorly is also tried turned 90°, 180° and
  270°, and a turn that reads clearly better is kept.
- **`.epub`**: converted with pandoc. **`.md`, `.txt`**: copied unchanged, so that a search
  of the output folder covers every source.
- Anything else is skipped and logged. `SOURCES.md`, `PDF-COVERAGE.md` and `.DS_Store` are
  ignored. If your own index of the sources is kept in the folder under another name, give
  it to `--skip`: a file named there is left alone and is not counted as skipped (without
  that, an index `INDEX.md` would be copied to `INDEX.md.txt` like any other `.md` file).

| Flag | Meaning |
|---|---|
| `--out DIR` | Where the text goes (default `SOURCES_DIR/text`). |
| `--workers N` | Share the work between N processes. |
| `--seconds S` | Stop after about this long. The PDF in hand keeps its finished pages, and the next run goes on from there. |
| `--min-chars N` | The threshold for OCR (default 80). |
| `--dpi-scale PIXELS` | The longer side of the page image made for OCR (default 2800). |
| `--no-rotate` | Try no turns. |
| `--redo FILE...` | Convert these files again from scratch, writing `NAME.txt.new` beside the old text and saying which pages differ. The old text is never replaced: that is yours to decide. |
| `--skip NAME...` | File names to leave alone: no text is made for them and they are not counted. |
| `--clear-locks` | Remove locks left by a run that was killed (see below). |
| `--tmp DIR` | Where to make the scratch folder for page images. |
| `--timeout SECONDS` | How long `pdftotext`, `pdftoppm` or pandoc may take over one call (default 120). |
| `--ocr-timeout SECONDS` | How long Tesseract may take over one page (default 600). |

A file that cannot be converted (a program fails or runs over its time) is reported as
`FAILED` with the reason, and the run goes on to the next; the exit code is then 1.

Where the system will not let the command remove a lock, a page cache or a part-written
file it made (some shells forbid deleting in a connected folder), it says so in one line on
standard error, `could not remove the lock .lock-NAME: Operation not permitted; remove it by
hand`, counts the file as converted if its text is complete, goes on, adds `; N could not be
removed` to the last line, and exits 1.

## The files the commands write

| Command | Writes | Where |
|---|---|---|
| `propose-edits` | The copy, and nothing else (the registry given with `--registry` is only read) | The path given to `--out`. While it is being put in place, a file `COPY.docx.partial-…` exists briefly beside it. |
| `file-tickets` | The results file (JSON: `index`, `title`, `id`, `outcome` per ticket), only with `--results` | The path given. Tickets themselves are written by Backlog, in the project. |
| `note-map` | The registry (JSON: for each note its `id`, `kind`, `label`, `text`, `sentence`, the SHA-256 of the saves it was first and last seen in, and the save it was retired in); the map, only with `--map`; the reading text (pandoc's markdown of the manuscript with permanent IDs for note numbers), only with `--extract` | The paths given. Each is written through a file `NAME.partial-…` beside it, which exists briefly. |
| `compare-saves` | Nothing | |
| `check-spacing` | Nothing | |
| `sources-to-text` | `NAME.txt` for each source (`NAME.txt.new` with `--redo`); `.convert-log.txt`, one line per file (`NAME pages=M ocr=K turned=T`, `NAME md`, `SKIP NAME`, `FAILED NAME: reason`); while a PDF is part done, `.NAME.pages.json`, its page cache, removed when the file completes; while a file is being converted, a lock folder `.lock-NAME`, removed when it is done | The output folder. |

Scratch files (the copy before it is verified, page images, committed versions fetched by
`--git`) go in a temporary folder that is removed when the command ends, also when it is
interrupted. No command writes anything beside its input, and none leaves a `__pycache__`.

## Errors and exit codes

| Code | Meaning |
|---|---|
| 0 | Complete success, including nothing to do. `compare-saves` exits 0 whether or not the saves differ. |
| 1 | The run happened and found a problem: an edit could not be placed, a check failed, a ticket failed, a note is unclear, a paragraph is not at the expected spacing, a source could not be converted, a save could not be read, the system refused the command a file. |
| 2 | The command refused to start: a bad flag, a missing program, a missing or faulty input, an output that exists. Nothing was done. |
| 130 | Interrupted (Ctrl-C). Nothing half-written is left behind, unless the system forbids removing it, which the command then says. |

What to do about the refusals and failures you are most likely to meet:

| Message | What to do |
|---|---|
| `… was not found` (pandoc, backlog, pdftotext, …) | Install it with the command in the message. |
| `… already exists; give another name or add --force` | `propose-edits` and `note-map --extract` will not write over a file. Choose another name, or add `--force`. |
| `… names a note by its permanent ID (N-0042); give the registry with --registry FILE` | Add `--registry` with the registry `note-map` keeps. |
| `N-0042 is retired …`, `… is not in the registry`, `the note N-0042 is not in this save` | The note the edit was written for is gone, or the ID is mistyped. Check the map. |
| `N-0042 cannot be placed in this save without guessing …` | Run `note-map` on this save and settle the unclear note with `--assign`; then run the edits again. |
| `no reading text: …; nothing written. To bring the registry up to date without it, run again without --extract` | pandoc failed, or counted the notes differently from the manuscript (a marker with no note, a note in a text box). Nothing was written, the registry included. Run without `--extract` to update the registry alone. |
| `stopped by the system: Operation not permitted: FILE` (or `Permission denied`, `No space left on device`) | The system would not let the command read or write that file. The run stopped there (exit 1); nothing is left half written. Put right the permission or the disk, and run again. |
| `could not remove … ; remove it by hand` | The system refused to let the command delete something it made. Delete the named file or folder yourself (or grant the permission and run again). |
| `"find" text not found …` | The text is not in the place searched. Check `where`, and that the text is copied exactly, curly quotes included. |
| `"find" text occurs N times …; add "occurrence"` | Add `"occurrence": 2` (or whichever). |
| `the "find" text crosses a note marker …` | Shorten the edit so that it lies on one side of the marker, or make two edits. |
| `… touches an existing tracked insertion` | Accept or reject that change in Word, save, and run again. |
| `Backlog has left a lock in the project: backlog/.locks/…` | Make sure no `backlog` command is running, then remove the lock folder by hand, or add `--ignore-locks`. The kit never removes one. |
| `… is not a Backlog project` | Run `backlog init` in that folder first. |
| `N notes are unclear …` | Add the `--assign` flags the listing shows, one per note. |
| `NAME is locked (.lock-NAME)` | Another `sources-to-text` may be working on it. If none is, run again with `--clear-locks`. |
| `verification failed` | A fault in `propose-edits`. No copy was kept; please report it. |

## Working with a book folder kept in git

The commands are designed around keeping the whole book folder (manuscript, sources,
tickets, note registry, records) in one private git repository, with every checked save of
the manuscript a commit. The kit itself never commits, pulls or pushes.

**Text diffs of Word files inside git.** In the book folder:

    printf '*.docx diff=docx\n' >> .gitattributes
    git config diff.docx.textconv "pandoc -f docx -t markdown-smart --wrap=none"

After which `git diff` and `git log -p` show the changed words (words only; formatting is
`compare-saves`' job):

```
-The lamp was lit at dusk, and the keeper isn’t one to waste oil.[^1]
+[^1]The lamp was lit at dawn, and the keeper isn’t one to waste oil.[^2]
```

The `git config` line is a setting of that clone, so it is typed once on each computer.

**A `.gitignore` for a book folder:**

    ~$*
    .DS_Store
    __pycache__/
    .locks/

**Two computers.** The author writes in Word on one, and the assistant works on another.
The author's routine after saving the manuscript is three commands:

    git add -A
    git commit -m "save"
    git push

The writing computer needs git (it comes with Apple's command line tools) and access to the
private repository; nothing from this kit, unless the text diff is wanted there, which needs
pandoc. On the assistant's computer `git pull` brings the save,
`compare-saves --git HEAD~1 MANUSCRIPT.docx` says what changed, and
`note-map MANUSCRIPT.docx --registry notes.json --map note-map.md --extract reading.md --force`
brings the registry, the map and the reading text up to date in one run. A `.docx` cannot be merged,
so each has one writer: the author. The assistant never commits a change to the manuscript.

**How proposed edits reach the author.** The copy `propose-edits` writes is committed under a
new name (`BOOK-proposed-2026-10-03.docx`), never as the manuscript, so a pull only ever adds
a file. The author opens the copy, accepts or rejects, and saves it as the manuscript. So
that the copy does not lack what the author wrote meanwhile, use one of two routines:

- *Taking turns* (the usual way): the author commits a save, says it is the assistant's turn,
  and does not write in the manuscript until the copy has been adopted.
- *Running the edits where the writing is done*: the assistant commits the edits file, not a
  copy; the author runs `propose-edits` on the writing computer against the current save (it
  needs only Apple's Python). An edit whose text has changed since is refused and listed.

Either way the author may have saved again before the edits are run, and every note number
may have moved; so an edits file should name a note by its permanent ID (`"where":
"N-0042"`, with `--registry`), not by `endnote:N`.

**Large files.** A hosting service may refuse a file over its limit (GitHub: 100 MB). Put
PDFs, images and other large binaries through [Git LFS](https://git-lfs.com), tracked before
their first commit (`git lfs install` once on each computer, then
`git lfs track "*.pdf" "*.png" "*.jpg"`). Keep the manuscript itself in ordinary git: LFS
takes over the diff setting and would defeat the text diff. A simpler alternative for
sources that never change is to leave them out of git and commit a list of their checksums.

**Size.** Word and PowerPoint files are already compressed, so every committed version costs
about its full size: the repository grows by the size of a save times the number of saves
committed. A manuscript of 5 MB with its figures in it, committed 200 times, is about 1 GB
of history, which is the most GitHub recommends for a repository; past that a clone is slow,
and **history cannot be trimmed afterwards without rewriting it**. So keep the figures out
of the manuscript until submission: put a placeholder line where each goes (`[Figure 3.2]`)
and keep the pictures as files of their own (through Git LFS, above). A save of text alone
is usually under 1 MB, and 200 of them a fifth of the limit. To see what the repository
holds now:

    git count-objects -vH

(`size-pack` is the history; files in Git LFS are not counted in it).

## Testing

    /usr/bin/python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
    .venv/bin/pytest        # the whole suite, with coverage
    .venv/bin/ruff check .  # lint

The suite needs none of pandoc, poppler, Tesseract, Backlog or git: each is replaced by a
small stand-in program on a `PATH` of its own, which records what it was given and can be
told to fail. Every document in the tests is invented and built by the tests themselves; no
real manuscript, source or ticket is in this repository.

Coverage of `booktools/` is 99% (statements and branches; 398 tests). The four statements
no test in the suite's own process runs are the lines of `sources-to-text` that only its
worker processes run (writing their tally, and the module's entry point), which the
`--workers` tests exercise in child processes where coverage is not measured.

`.venv/bin/pytest -m tier1` runs the tests of pure functions alone, and `-m tier2` the tests
of whole commands.

**Checks to make by hand against real files**, which the suite cannot make. All are
read-only on your book folder; write only into a scratch folder.

1. `compare-saves` on two consecutive real saves: the changes you know you made, and nothing
   else.
2. `check-spacing` on the manuscript: the counts you expect.
3. `sources-to-text --redo` on a few sources *copied into a scratch folder with their
   existing text*: the new text matches the old, or differs only as the programs' versions
   explain.
4. `propose-edits --dry-run` with a few edits against a *copy* of the manuscript: each is
   found where you expect. Then apply them, and open the copy in Word.
5. `note-map` over three consecutive saves with the registry in a scratch folder: every ID
   carried, none unclear. With `--extract`, read the text: each ID stands at the marker and
   the note you expect.
6. With Pillow installed, `sources-to-text` on a PDF with a page scanned sideways: the
   page's header says it was turned, and the text under it reads properly.

## Known limitations

- **`propose-edits`** makes changes within one paragraph only. Not in this version:
  inserting, deleting, splitting or joining whole paragraphs; changes to formatting alone;
  moves; an edit that crosses a note marker, tab, line break, picture, bookmark, field or
  the edge of a hyperlink or comment; text inside a text box or drawing (it is not
  searched). Make those by hand in Word.
- **A note is shown "as the book numbers it"** on the assumption that notes are numbered
  1, 2, 3 from 1, continuously or restarting in each section. Other number formats and a
  start other than 1 are not read. A footnote numbered afresh on each page is shown by its
  count alone.
- **`compare-saves`** shows a moved paragraph as one removed and one added, and a paragraph
  split or joined as one changed and one added or removed; among identical paragraphs the
  pairing is by order. An empty paragraph is not counted, and of a paragraph holding a text
  box only the box's own paragraphs are compared.
- **`note-map`** recognises a note by its text and its sentence. Its rule for finding
  sentences is simple and can be fooled by unusual punctuation; what matters is that it
  gives the same answer for the same text at every save.
- **`note-map --extract`** relies on pandoc numbering the notes in the order their markers
  come, endnotes and footnotes together, and refuses when the counts differ; a document
  with a note marker inside a text box, or a marker whose note is missing, gets no reading
  text. A literal `[^7]` typed in the manuscript is safe: pandoc writes it with backslashes.
- **`file-tickets`** knows a ticket's title, description, priority, labels, milestone, status
  and comments, and nothing else: no assignee, acceptance criteria or dependencies. Any
  other key in a tickets file is refused as an unknown key; set those in Backlog afterwards.
- **`sources-to-text`** reads only the files directly in the folder, not sub-folders.
  Turning pages needs Pillow.

**Deliberately not part of the kit:** packaging a submission, review copies, art decks,
any one publisher's rules, a manuscript-wide "is it ready" check, a graphical interface,
network access, calls to an AI model, and any editing of a manuscript in place.

## Notes for users

Dated lines about anything a user of the commands, or a reader of what they write, needs to
know. The first version of each command was built on 3 October 2026.

- 3 October 2026: `propose-edits` marks whole words, not letters within a word, and the new
  words take the formatting of the text they replace.
- 3 October 2026: `propose-edits` exits 1 (not 2) when an edit cannot be placed; 2 is kept
  for a faulty edits file and other refusals to start.
- 3 October 2026: `compare-saves` pairs paragraphs by their text. New line forms: `ADDED`,
  `REMOVED`, and the label `j (old i)` where a paragraph's index differs between the saves.
  No font name is treated as ignorable unless given with `--ignore-font`.
- 3 October 2026: `check-spacing` reports `FOOTNOTES` as well as `TEXT` and `NOTES`, takes
  `--expect`, and exits 1 when any paragraph does not match.
- 3 October 2026: `sources-to-text` copies `.txt` sources as well as `.md`; a program that
  fails now fails the file, with the reason, instead of writing an empty page.
- 3 October 2026: `check-spacing` no longer counts the separator entries Word keeps among
  the notes (two fewer paragraphs under `NOTES` than before, and no `FOOTNOTES` block for
  a book without footnotes), so a manuscript double spaced throughout now exits 0.
- 3 October 2026: in `compare-saves`, a small change in a long paragraph is one short
  `TEXT` line (it could be several lines of unrelated text), and the text diff no longer
  reports the blank line that comes and goes with a note.
- 3 October 2026: page turning in `sources-to-text` was checked with the real Pillow
  (12.3.0) and Tesseract (5.5.3): pages scanned sideways and upside down are found and
  read. On a map whose labels run in every direction the choice of turn is a toss-up.
- 3 October 2026: `file-tickets` checks the priority, labels, milestone and status of each
  ticket it reads back, as well as its title, description and comments.
- 5 October 2026: `note-map` has a new flag, `--extract FILE` (with `--force` and
  `--timeout`): a reading text of the manuscript, pandoc's markdown with each note's
  permanent ID in place of its number (`[^N-0042]`), and the number the book prints in a
  comment at the note. It needs pandoc. Records and edits files can now be written from a
  text that already names notes by ID.
- 5 October 2026: in an edits file, `where` may be a note's permanent ID (`"where":
  "N-0042"`), with the new flag `--registry FILE` on `propose-edits`. The same edits file
  then works against a later save in which the notes have been renumbered. The report shows
  such a note as `N-0042 → Chapter 3, note 7 (endnote:42)`. The message for a `where` that
  cannot be read now mentions the ID form.
- 5 October 2026: the dry run and the report of `propose-edits` have a new kind of line,
  `note: accepting ID leaves two spaces in a row: "…"`, under an edit that would leave a
  doubled or missing space or punctuation mark at its edges. Anything that reads the report
  line by line should expect it. It does not change the exit code.
- 5 October 2026: **the text diff of `compare-saves` has a new line form, `CHANGED:`**. A
  changed paragraph or note of more than 200 characters is now shown as its changed words
  only (`  CHANGED: …25 characters[old → new]25 characters…`) where it used to be printed
  whole twice as `OLD:` and `NEW:`. The new flag `--full-diff` gives the earlier output
  exactly. Shorter paragraphs are reported as before.
- 5 October 2026: where the system refuses to let a command remove a lock, a page cache or
  a part-written file it made, the command now says `could not remove …; remove it by hand`
  on standard error instead of stopping with a Python traceback. `sources-to-text` then goes
  on, ends its last line with `; N could not be removed`, and exits 1.
- 5 October 2026: when the system refuses a command a file it must read or write (no
  permission, a full disk), every command now stops with one line, `stopped by the system:
  REASON: FILE`, and exit code 1, where it used to stop with a Python traceback.
- 5 October 2026: when `note-map --extract` cannot make the reading text, its message now
  ends by saying how to update the registry alone (run again without `--extract`).
- 5 October 2026: nothing changed in `sources-to-text --skip`, but note what it is for: name
  your own index file of the sources there and it is neither copied nor counted.
- 5 October 2026: advice added on the size of a book folder kept in git (keep figures out
  of the manuscript until submission; `git count-objects -vH`).

## Contributing

Development is test-first: every piece of behaviour starts as a failing test. The test
runner and linter (`pytest`, `pytest-cov`, `ruff`) are in `requirements-dev.txt` and are
needed only for development, never to run the commands. `python3 -m
tests.fixtures.make_fixtures` regenerates the sample documents.

## Licence

MIT. See [LICENSE](LICENSE).
