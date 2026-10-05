import json
import zipfile
from datetime import datetime, timezone

import pytest

from booktools.propose_edits import main
from tests.docxkit import pack_docx
from tests.samples import SAMPLE_EDITS, edited_parts, moved_and_rewritten, sample_parts

pytestmark = pytest.mark.tier2


def clock():
    return datetime(2026, 10, 3, 13, 46, 20, tzinfo=timezone.utc)


class Book:
    """A sample manuscript and edits file in a folder of their own."""

    def __init__(self, tmp_path, edits=SAMPLE_EDITS, parts=None):
        self.folder = tmp_path / "book"
        self.folder.mkdir()
        self.manuscript = self.folder / "in.docx"
        pack_docx(self.manuscript, parts or sample_parts())
        self.edits = self.folder / "edits.json"
        self.edits.write_text(json.dumps(edits), encoding="utf-8")
        self.out = tmp_path / "out" / "new.docx"
        self.out.parent.mkdir()
        self.scratch = tmp_path / "scratch"
        self.scratch.mkdir()

    def run(self, *flags):
        args = [str(self.edits), "--in", str(self.manuscript), "--out", str(self.out)]
        return main(args + ["--tmp", str(self.scratch)] + list(flags), now=clock)


@pytest.fixture
def book(tmp_path):
    return Book(tmp_path)


STAMP = (
    ' w:author="Claude" w:date="2026-10-03T14:46:00Z" w16du:dateUtc="2026-10-03T13:46:00Z"'
)


def test_writes_a_copy_with_the_edits_as_tracked_changes_and_reports_each(book, capsys):
    assert book.run() == 0
    assert capsys.readouterr().out.splitlines() == [
        "E1 | body, paragraph 3 | … at dusk, and the keeper [isn’t → is not]"
        " one to waste oil. | no contractions | PASS",
        "E2 | body, paragraph 4 | … wrote every figure in a [large  →]ledger. | cut | PASS",
        "E3 | Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London]"
        " in the station log. | place | PASS",
        "reject all: PASS: every paragraph reads as in the original",
        "accept all: PASS: the original with exactly the 3 edits made",
        "revisions: PASS: 4 revisions for 3 edits, all by Claude at 2026-10-03T14:46:00Z",
        "package: PASS: 2 parts changed, each well-formed; everything else byte-identical",
        f"wrote {book.out}",
    ]
    with zipfile.ZipFile(book.out) as copy:
        body = copy.read("word/document.xml").decode("utf-8")
    assert (
        f'<w:del w:id="3"{STAMP}><w:r><w:delText>isn’t</w:delText></w:r></w:del>'
        f'<w:ins w:id="4"{STAMP}><w:r><w:t>is not</w:t></w:r></w:ins>' in body
    )


def snapshot(folder):
    return {path.name: path.read_bytes() for path in folder.iterdir()}


def test_the_manuscript_and_its_folder_are_left_exactly_as_they_were(book):
    before = snapshot(book.folder)
    assert book.run() == 0
    assert snapshot(book.folder) == before
    assert list(book.scratch.iterdir()) == []  # the scratch folder was removed


def test_every_entry_but_the_edited_parts_is_byte_identical_in_the_copy(book):
    book.run()
    with zipfile.ZipFile(book.manuscript) as old, zipfile.ZipFile(book.out) as new:
        assert new.namelist() == old.namelist()
        differing = [n for n in old.namelist() if old.read(n) != new.read(n)]
    assert differing == ["word/document.xml", "word/endnotes.xml"]


def test_dry_run_prints_the_same_lines_and_writes_nothing(book, capsys):
    assert book.run("--dry-run") == 0
    assert capsys.readouterr().out.splitlines() == [
        "E1 | body, paragraph 3 | … at dusk, and the keeper [isn’t → is not]"
        " one to waste oil. | no contractions | found",
        "E2 | body, paragraph 4 | … wrote every figure in a [large  →]ledger. | cut | found",
        "E3 | Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London]"
        " in the station log. | place | found",
        f"dry run: 3 edits found; {book.out} would be written; nothing written",
    ]
    assert not book.out.exists()
    assert list(book.scratch.iterdir()) == []


def refused(book, capsys, *flags):
    """Run expecting a refusal to start: exit 2, nothing on stdout, nothing written."""
    existed = book.out.exists()
    assert book.run(*flags) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert book.out.exists() == existed
    return captured.err.splitlines()


def test_refuses_to_start_without_a_usable_edits_file(book, capsys):
    book.edits.unlink()
    assert refused(book, capsys) == [f"propose-edits: {book.edits}: no such file"]
    book.edits.write_text('[{"find": "a", "replace": "a"}, {"fnd": "x"}]')
    assert refused(book, capsys) == [
        f"propose-edits: {book.edits} cannot be used:",
        '  edit 1: "replace" is the same as "find", so the edit would change nothing',
        '  edit 2: unknown key "fnd"',
        '  edit 2: "find" must be text and not empty',
        '  edit 2: "replace" must be text (empty to delete)',
    ]


def test_refuses_to_start_without_a_usable_manuscript(book, capsys):
    book.manuscript.write_text("not a zip")
    assert refused(book, capsys) == [
        f"propose-edits: {book.manuscript}: not a .docx file (it is not a zip archive)"
    ]


def test_refuses_to_write_over_an_existing_file_without_force(book, capsys):
    book.out.write_text("something already here")
    assert refused(book, capsys) == [
        f"propose-edits: {book.out} already exists; give another name or add --force"
    ]
    assert book.out.read_text() == "something already here"
    assert refused(book, capsys, "--dry-run") == [
        f"propose-edits: {book.out} already exists; give another name or add --force"
    ]
    assert book.run("--force") == 0
    assert zipfile.is_zipfile(book.out)


def test_never_writes_over_the_manuscript_even_with_force(book, capsys):
    before = book.manuscript.read_bytes()
    book.out = book.folder / "." / "in.docx"  # the same file by another spelling
    assert refused(book, capsys, "--force") == [
        f"propose-edits: {book.out} is the manuscript itself; a copy must have another name"
    ]
    assert book.manuscript.read_bytes() == before


def test_refuses_when_the_folder_for_the_copy_does_not_exist(book, capsys):
    book.out = book.out.parent / "missing" / "new.docx"
    assert refused(book, capsys) == [
        f"propose-edits: the folder {book.out.parent} does not exist"
    ]


def test_a_usage_error_exits_2_and_help_exits_0(book, capsys):
    assert main(["--in", "x.docx"]) == 2
    assert "usage: propose-edits" in capsys.readouterr().err
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    for flag in ("--in", "--out", "--author", "--dry-run", "--force", "--tmp"):
        assert flag in out


def test_edits_that_cannot_be_placed_exit_1_and_nothing_is_written(tmp_path, capsys):
    edits = [
        {"id": "ok", "find": "March", "replace": "April"},
        {"id": "gone", "find": "no such words", "replace": "x"},
        {"id": "twice", "find": "the", "replace": "a"},
    ]
    book = Book(tmp_path, edits)
    for flags in ((), ("--dry-run",)):
        assert book.run(*flags) == 1
        captured = capsys.readouterr()
        assert captured.out.splitlines() == [
            "ok | body, paragraph 9 | The log for [March → April] is missing. | | found"
        ]
        assert captured.err.splitlines() == [
            "propose-edits: 2 of 3 edits cannot be made; nothing written:",
            '  edit 2 (gone): "find" text not found in the body',
            '  edit 3 (twice): "find" text occurs 2 times in the body (paragraphs 3 and 6);'
            ' add "occurrence" to say which',
        ]
        assert not book.out.exists()


def test_an_empty_edits_file_succeeds_and_writes_no_copy(tmp_path, capsys):
    book = Book(tmp_path, edits=[])
    assert book.run() == 0
    assert capsys.readouterr().out == "no edits, nothing written\n"
    assert not book.out.exists()


def revisions(book):
    """(element, attributes) of every tracked change in the copy."""
    import re

    with zipfile.ZipFile(book.out) as copy:
        xml = copy.read("word/document.xml") + copy.read("word/endnotes.xml")
    return re.findall(r"<w:(ins|del) ([^>]*)>", xml.decode("utf-8"))


def test_author_and_date_land_on_every_revision(book):
    assert book.run("--author", "A. N. Editor", "--date", "2026-07-01T09:30:45") == 0
    found = revisions(book)
    assert [name for name, _ in found] == ["del", "ins", "del", "ins"]
    body = 'w:author="A. N. Editor" w:date="2026-07-01T09:30:00Z" w16du:dateUtc="2026-07-01T08:30:00Z"'
    note = 'w:author="A. N. Editor" w:date="2026-07-01T09:30:00Z"'
    assert [attrs.split(" ", 1)[1] for _, attrs in found] == [body, body, body, note]


def test_a_date_with_an_offset_is_an_instant_and_utc_writes_utc(book):
    assert book.run("--date", "2026-07-01T09:30:00+02:00") == 0
    assert 'w:date="2026-07-01T08:30:00Z" w16du:dateUtc="2026-07-01T07:30:00Z"' in revisions(book)[0][1]
    assert book.run("--force", "--utc", "--date", "2026-07-01T09:30:00Z") == 0
    assert 'w:date="2026-07-01T09:30:00Z" w16du:dateUtc="2026-07-01T09:30:00Z"' in revisions(book)[0][1]
    # Without --date the clock is used, and with --utc it is written as UTC.
    assert book.run("--force", "--utc") == 0
    assert 'w:date="2026-10-03T13:46:00Z"' in revisions(book)[0][1]


def test_a_date_that_cannot_be_read_is_refused(book, capsys):
    assert refused(book, capsys, "--date", "last Tuesday") == [
        "propose-edits: --date must be like 2026-10-03T14:46 (London time, or UTC with --utc),"
        " or carry an offset such as +01:00 or Z"
    ]


def spoil(monkeypatch, old, new):
    """Make the command write a copy in which `old` has become `new`."""
    import booktools.propose_edits as command

    real = command.apply

    def spoilt(parts, located, author, dates):
        out = real(parts, located, author, dates)
        assert old in out["word/document.xml"]
        out["word/document.xml"] = out["word/document.xml"].replace(old, new, 1)
        return out

    monkeypatch.setattr(command, "apply", spoilt)


def test_a_copy_that_fails_verification_is_not_kept_and_the_exit_code_is_1(book, capsys, monkeypatch):
    spoil(monkeypatch, "<w:t>is not</w:t>", "<w:t>is surely not</w:t>")
    assert book.run() == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "E1 | body, paragraph 3 | … at dusk, and the keeper [isn’t → is not]"
        " one to waste oil. | no contractions | FAIL",
        "E2 | body, paragraph 4 | … wrote every figure in a [large  →]ledger. | cut | PASS",
        "E3 | Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London]"
        " in the station log. | place | PASS",
        "reject all: PASS: every paragraph reads as in the original",
        "accept all: FAIL: paragraph 3 of word/document.xml reads"
        " '… dusk, and the keeper is surely not one to waste oil.' but the edits ask for"
        " '… dusk, and the keeper is not one to waste oil.'",
        "revisions: PASS: 4 revisions for 3 edits, all by Claude at 2026-10-03T14:46:00Z",
        "package: PASS: 2 parts changed, each well-formed; everything else byte-identical",
    ]
    assert captured.err.splitlines() == [
        f"propose-edits: verification failed; {book.out} was not written"
    ]
    assert not book.out.exists()
    assert list(book.scratch.iterdir()) == []


def test_keep_on_failure_keeps_the_failed_copy_for_inspection(book, capsys, monkeypatch):
    spoil(monkeypatch, "<w:t>is not</w:t>", "<w:t>is surely not</w:t>")
    assert book.run("--keep-on-failure") == 1
    assert capsys.readouterr().err.splitlines() == [
        f"propose-edits: verification failed; the failed copy was kept at {book.out}"
    ]
    assert zipfile.is_zipfile(book.out)


def test_a_copy_whose_picture_or_other_entry_changed_fails_the_package_check(book, capsys, monkeypatch):
    from booktools.docx import Docx

    real = Docx.write_copy

    def careless(self, path, replaced):
        real(self, path, replaced)
        with zipfile.ZipFile(path) as written:
            entries = [(info, written.read(info)) for info in written.infolist()]
        with zipfile.ZipFile(path, "w") as spoilt:
            for info, data in entries:
                spoilt.writestr(info, data + b"!" if info.filename.endswith(".png") else data)

    monkeypatch.setattr(Docx, "write_copy", careless)
    assert book.run() == 1
    assert capsys.readouterr().out.splitlines()[-1] == (
        "package: FAIL: word/media/image1.png is not byte-identical in the copy"
    )
    assert not book.out.exists()


def test_an_interrupted_run_leaves_nothing_behind_and_exits_130(book, capsys, monkeypatch):
    import booktools.propose_edits as command

    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(command, "verify", interrupt)
    assert book.run() == 130
    assert capsys.readouterr().err.splitlines() == ["propose-edits: interrupted; nothing written"]
    assert not book.out.exists()
    assert list(book.scratch.iterdir()) == []
    assert [path.name for path in book.out.parent.iterdir()] == []


def test_a_document_that_already_holds_tracked_changes(tmp_path, capsys):
    from tests.samples import BODY_PARAGRAPHS

    theirs = (
        '<w:ins w:id="40" w:author="Ed" w:date="2026-09-30T10:00:00Z">'
        '<w:r><w:t xml:space="preserve"> Truly.</w:t></w:r></w:ins>'
        '<w:del w:id="41" w:author="Ed" w:date="2026-09-30T10:00:00Z">'
        '<w:r><w:delText xml:space="preserve"> Gone.</w:delText></w:r></w:del>'
    )
    body = list(BODY_PARAGRAPHS)
    body[8] = body[8].replace("</w:p>", theirs + "</w:p>")
    edits = [{"id": "ok", "find": "March", "replace": "April"}]
    book = Book(tmp_path, edits, sample_parts(body))
    assert book.run() == 0
    with zipfile.ZipFile(book.out) as copy:
        xml = copy.read("word/document.xml").decode("utf-8")
    assert theirs in xml  # the earlier changes are untouched
    assert f'<w:del w:id="42"{STAMP}>' in xml and f'<w:ins w:id="43"{STAMP}>' in xml
    assert "revisions: PASS: 2 revisions for 1 edit, all by Claude" in capsys.readouterr().out

    book.edits.write_text(json.dumps([{"find": "missing. Truly", "replace": "missing"}]))
    assert book.run("--force") == 1
    assert capsys.readouterr().err.splitlines()[1] == (
        '  edit 1: the "find" text touches an existing tracked insertion;'
        " accept or reject that change in Word first"
    )


def test_line_endings_inside_the_xml_are_kept_as_they_were(tmp_path):
    parts = sample_parts()
    parts["word/document.xml"] = parts["word/document.xml"].replace("</w:p>", "</w:p>\r\n")
    book = Book(tmp_path, parts=parts)
    assert book.run() == 0
    with zipfile.ZipFile(book.manuscript) as old, zipfile.ZipFile(book.out) as new:
        before, after = old.read("word/document.xml"), new.read("word/document.xml")
    assert after.count(b"\r\n") == before.count(b"\r\n") == 10
    assert b"\n" not in after.replace(b"\r\n", b"")


def test_text_stored_decomposed_is_found_by_an_edit_typed_composed(tmp_path, capsys):
    from tests.samples import BODY_PARAGRAPHS, p

    body = list(BODY_PARAGRAPHS) + [p("The cafe\u0301 by the pier.")]
    edits = [{"find": "caf\u00e9 by", "replace": "caf\u00e9 near"}]
    book = Book(tmp_path, edits, sample_parts(body))
    assert book.run() == 0
    assert capsys.readouterr().out.splitlines()[0] == (
        "edit 1 | body, paragraph 10 | The cafe\u0301 [by → near] the pier. | | PASS"
    )


def test_edits_in_a_table_cell_and_in_a_footnote(tmp_path, capsys):
    edits = [
        {"id": "cell", "find": "12 pints", "replace": "14 pints"},
        {"id": "foot", "where": "footnote:1", "find": "Imperial", "replace": "British"},
        {"id": "any", "where": "all", "find": "Ibid.", "replace": "Ibidem."},
    ]
    book = Book(tmp_path, edits)
    assert book.run() == 0
    assert capsys.readouterr().out.splitlines()[:3] == [
        "cell | body, paragraph 5 | Oil used: [12 → 14] pints | | PASS",
        "any | Chapter 2, note 2 (endnote:2) |  [Ibid → Ibidem]. | | PASS",
        "foot | Chapter 1, note 1 (footnote:1) |  [Imperial → British] pints. | | PASS",
    ]


def test_an_interruption_while_the_copy_is_put_in_place_leaves_no_part_written_file(
    book, capsys, monkeypatch
):
    import shutil

    def cut_short(source, target, **_):
        with open(target, "wb") as file:
            file.write(b"half a file")
        raise KeyboardInterrupt

    # However the finished copy is carried to its place, it is cut off half way.
    monkeypatch.setattr(shutil, "copyfile", cut_short)
    monkeypatch.setattr(shutil, "move", cut_short)
    assert book.run() == 130
    assert [path.name for path in book.out.parent.iterdir()] == []
    assert capsys.readouterr().err.splitlines() == ["propose-edits: interrupted; nothing written"]


def test_with_force_an_interrupted_run_leaves_the_earlier_file_as_it_was(book, monkeypatch):
    import shutil

    def cut_short(source, target, **_):
        with open(target, "wb") as file:
            file.write(b"half a file")
        raise KeyboardInterrupt

    monkeypatch.setattr(shutil, "copyfile", cut_short)
    monkeypatch.setattr(shutil, "move", cut_short)
    book.out.write_text("the earlier copy")
    assert book.run("--force") == 130
    assert book.out.read_text() == "the earlier copy"
    assert [path.name for path in book.out.parent.iterdir()] == ["new.docx"]


BY_ID = [{"id": "E3", "where": "N-0001", "find": "Trinity House", "replace": "Trinity House, London"}]


def registered(book, *saves):
    """A registry in a folder of its own that has seen `saves` in turn (the sample by default)."""
    from booktools.note_map import main as note_map

    records = book.folder.parent / "records"
    records.mkdir()
    book.registry = records / "notes.json"
    for number, parts in enumerate(saves or [sample_parts()]):
        save = records / f"save{number}.docx"
        pack_docx(save, parts)
        assert note_map([str(save), "--registry", str(book.registry)]) == 0
        save.unlink()
    return book.registry


def test_an_edit_naming_a_note_by_its_permanent_id_lands_in_that_note_whatever_its_number(
    tmp_path, capsys
):
    book = Book(tmp_path, BY_ID)
    registry = registered(book)
    before = registry.read_bytes()
    capsys.readouterr()
    assert book.run("--registry", str(registry), "--dry-run") == 0
    assert capsys.readouterr().out.splitlines()[0] == (
        "E3 | N-0001 → Chapter 1, note 1 (endnote:1) | …Recorded by Trinity House[→ , London]"
        " in the station log. | | found"
    )
    # The same edits file against a later save, in which a note was added in front.
    pack_docx(book.manuscript, edited_parts())
    assert book.run("--registry", str(registry)) == 0
    assert capsys.readouterr().out.splitlines()[0] == (
        "E3 | N-0001 → Chapter 1, note 2 (endnote:2) | …Recorded by Trinity House[→ , London]"
        " in the station log. | | PASS"
    )
    with zipfile.ZipFile(book.out) as copy:
        notes = copy.read("word/endnotes.xml").decode("utf-8")
    assert notes.count("<w:ins ") == 1
    assert notes.index("A note added") < notes.index("<w:ins ") < notes.index("Ibid.")
    assert registry.read_bytes() == before
    assert [path.name for path in registry.parent.iterdir()] == ["notes.json"]


def test_an_edit_by_id_needs_the_registry_and_a_registry_that_can_be_read(tmp_path, capsys):
    book = Book(tmp_path, BY_ID)
    assert refused(book, capsys) == [
        "propose-edits: edit 1 (E3) names a note by its permanent ID (N-0001);"
        " give the registry with --registry FILE"
    ]
    missing = tmp_path / "nowhere.json"
    assert refused(book, capsys, "--registry", str(missing)) == [
        f"propose-edits: {missing}: no such file"
    ]
    missing.write_text("[]")
    assert refused(book, capsys, "--registry", str(missing)) == [
        f"propose-edits: {missing} cannot be used: it is not a note registry written by note-map"
    ]
    assert not book.out.exists()


def test_the_registry_is_never_the_copy_to_write_and_is_not_read_when_no_edit_needs_it(
    book, capsys, tmp_path
):
    registry = tmp_path / "notes.json"
    registry.write_text("not a registry at all")
    assert book.run("--registry", str(registry), "--dry-run") == 0  # no edit names an ID
    capsys.readouterr()
    assert book.run("--registry", str(registry), "--out", str(registry), "--force") == 2
    assert capsys.readouterr().err.splitlines() == [
        f"propose-edits: {registry} is the registry; a copy must have another name"
    ]
    assert registry.read_text() == "not a registry at all"


def test_an_id_that_cannot_be_placed_is_named_with_the_reason_and_nothing_is_written(
    tmp_path, capsys
):
    edits = [
        {"id": "ok", "find": "March", "replace": "April"},
        {"id": "unknown", "where": "N-0042", "find": "Ibid", "replace": "Idem"},
        {"id": "retired", "where": "N-0001", "find": "note", "replace": "remark"},
    ]
    book = Book(tmp_path, edits)
    # The registry saw the edited save first, whose first note the sample does not have.
    registry = registered(book, edited_parts(), sample_parts())
    before = registry.read_bytes()
    capsys.readouterr()
    assert book.run("--registry", str(registry)) == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "ok | body, paragraph 9 | The log for [March → April] is missing. | | found"
    ]
    assert captured.err.splitlines() == [
        "propose-edits: 2 of 3 edits cannot be made; nothing written:",
        "  edit 2 (unknown): N-0042 is not in the registry",
        "  edit 3 (retired): N-0001 is retired: its note was already gone from an earlier save",
    ]
    assert not book.out.exists() and registry.read_bytes() == before


def test_an_id_whose_note_is_unclear_in_this_save_is_not_guessed(tmp_path, capsys):
    book = Book(tmp_path, BY_ID, parts=moved_and_rewritten())
    registry = registered(book)
    capsys.readouterr()
    assert book.run("--registry", str(registry)) == 1
    assert capsys.readouterr().err.splitlines() == [
        "propose-edits: 1 of 1 edit cannot be made; nothing written:",
        "  edit 1 (E3): N-0001 cannot be placed in this save without guessing (it may be"
        " endnote:1); run note-map on this save to settle it",
    ]
    assert not book.out.exists()


def test_help_names_the_registry_flag(capsys):
    assert main(["--help"]) == 0
    assert "--registry" in capsys.readouterr().out


def test_the_dry_run_and_the_report_note_an_edit_that_would_leave_two_spaces(tmp_path, capsys):
    from tests.samples import p

    edits = [{"id": "C", "find": "A second sentence.", "replace": ""}]
    book = Book(tmp_path, edits, parts=sample_parts([p("One sentence. A second sentence. A third.")]))
    note = 'note: accepting C leaves two spaces in a row: "…sentence.  A third."'
    assert book.run("--dry-run") == 0
    assert capsys.readouterr().out.splitlines() == [
        "C | body, paragraph 1 | One sentence. [A second sentence. →] A third. | | found",
        note,
        f"dry run: 1 edit found; {book.out} would be written; nothing written",
    ]
    assert book.run() == 0  # a note is not a failure: the edit is made as asked
    assert capsys.readouterr().out.splitlines()[:2] == [
        "C | body, paragraph 1 | One sentence. [A second sentence. →] A third. | | PASS",
        note,
    ]


def test_a_part_written_copy_that_cannot_be_removed_is_reported_not_a_traceback(
    book, capsys, monkeypatch
):
    import os
    import shutil

    from tests.stubs import forbid_removal

    def cut_short(source, target, **_):
        with open(target, "wb") as file:
            file.write(b"half a file")
        raise KeyboardInterrupt

    monkeypatch.setattr(shutil, "copyfile", cut_short)
    forbid_removal(monkeypatch, ".partial-")
    assert book.run() == 130
    assert capsys.readouterr().err.splitlines() == [
        f"propose-edits: could not remove the part-written file {book.out}.partial-{os.getpid()}:"
        " Operation not permitted; remove it by hand",
        "propose-edits: interrupted; nothing written",
    ]
    assert not book.out.exists()


def test_a_copy_the_system_will_not_let_be_written_is_one_line_and_exit_1(
    book, capsys, monkeypatch
):
    import os

    def refuse(source, target):
        raise PermissionError(1, "Operation not permitted", str(target))

    monkeypatch.setattr(os, "replace", refuse)
    assert book.run() == 1
    assert capsys.readouterr().err.splitlines() == [
        f"propose-edits: stopped by the system: Operation not permitted: {book.out}"
    ]
    assert [path.name for path in book.out.parent.iterdir()] == []  # no part-written file
    assert list(book.scratch.iterdir()) == []
