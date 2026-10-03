"""Stand-ins for the outside programs, put on a PATH of their own for one test.

Each records the arguments it was given, one JSON object per line in `calls.jsonl`
beside it, and behaves as `control.json` beside it says.
"""

import json
import os
import stat
import sys

BACKLOG = r'''
import json, os, re, sys, time

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "control.json")) as file:
    control = json.load(file)
args = sys.argv[1:]
with open(os.path.join(here, "calls.jsonl"), "a") as file:
    file.write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")

state_path = os.path.join("backlog", "stub-state.json")
state = {"creates": 0, "tasks": []}
if os.path.exists(state_path):
    with open(state_path) as file:
        state = json.load(file)


def save():
    with open(state_path, "w") as file:
        json.dump(state, file)


def tidy(text):
    return re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n")).strip()


def option(names):
    for name in names:
        if name in args:
            return args[args.index(name) + 1]
    return None


def find(id):
    for task in state["tasks"]:
        if task["id"].lower() == id.lower():
            return task
    print(f"Task {id} not found.", file=sys.stderr)
    sys.exit(1)


if not os.path.exists(os.path.join("backlog", "config.yml")):
    print("No Backlog.md project found. Run `backlog init` to initialize.")
    sys.exit(0)

if control.get("hang_on_help") and "--help" in args:
    time.sleep(60)
if control.get("create_dies_silently") and args[:2] == ["task", "create"]:
    sys.exit(3)
if args[:3] == ["task", "view", "--help"]:
    print("Options:\n  --plain" + ("" if control.get("no_json") else "\n  --json"))
elif args[:2] == ["task", "create"]:
    state["creates"] += 1
    attempt = state["creates"]
    save()
    if attempt == control.get("hang_on_create"):
        time.sleep(60)
    if attempt in control.get("fail_create", []):
        print("Invalid status: Nonsense. Valid statuses are: To Do, In Progress, Done")
        sys.exit(1)
    number = len(state["tasks"]) + 1 + control.get("ids_start_after", 0)
    description = option(["-d", "--description"])
    if attempt == control.get("mangle_create"):
        description = description.replace("$", "")  # what a shell would have done
    labels = option(["-l", "--labels"])
    state["tasks"].append({
        "id": f"TASK-{number}",
        "title": args[args.index("--") + 1],
        "description": tidy(description) if description is not None else None,
        "status": option(["-s", "--status"]) or "To Do",
        "priority": (option(["--priority"]) or "").lower() or None,
        "labels": labels.split(",") if labels else [],
        "milestone": option(["-m", "--milestone"]),
        "comments": [],
    })
    save()
    if control.get("leave_lock"):
        os.makedirs(os.path.join("backlog", ".locks", f"task-{number}"), exist_ok=True)
    if attempt == control.get("silent_create"):
        sys.exit(0)
    if attempt == control.get("garbage_create"):
        print("\x00\x01 unexpected")
        sys.exit(0)
    print(f"Created task TASK-{number}\nFile: {os.getcwd()}/backlog/tasks/task-{number}.md")
elif args[:2] == ["task", "edit"]:
    task = find(args[2])
    if control.get("fail_comment"):
        print("Could not update task", file=sys.stderr)
        sys.exit(1)
    task["comments"].append({
        "index": len(task["comments"]) + 1,
        "body": tidy(option(["--comment"])),
        "author": option(["--comment-author"]),
        "createdAt": "2026-10-03T15:36:00Z",
    })
    save()
    print(f"Updated task {task['id']}")
elif args[:2] == ["task", "view"]:
    task = find(args[2])
    if control.get("garbage_view"):
        print("not json at all")
    else:
        print(json.dumps({"schemaVersion": 1, "kind": "task-view", "task": task}))
elif args[:2] == ["task", "list"]:
    print(json.dumps({"schemaVersion": 1, "kind": "task-list", "tasks": state["tasks"]}))
else:
    print("stub backlog: unexpected arguments", args, file=sys.stderr)
    sys.exit(64)
'''


PANDOC = r'''
import html, json, os, re, sys, time, zipfile

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "control.json")) as file:
    control = json.load(file)
args = sys.argv[1:]
with open(os.path.join(here, "calls.jsonl"), "a") as file:
    file.write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")

if control.get("hang"):
    time.sleep(60)
if control.get("fail"):
    print("pandoc: could not read the file", file=sys.stderr)
    sys.exit(1)
if control.get("silent"):
    sys.exit(0)
if control.get("garbage"):
    sys.stdout.buffer.write(b"\xff\xfe not text")
    sys.exit(0)

# A very small imitation of pandoc reading a .docx as markdown: one line per
# paragraph, a blank line after each, note references numbered in order, then
# the notes.
source = next(arg for arg in args if arg.endswith(".docx") or arg.endswith(".epub"))
if source.endswith(".epub"):
    text = "plain text of " + os.path.basename(source) + "\n"
else:
    archive = zipfile.ZipFile(source)
    notes = {}
    for kind in ("endnote", "footnote"):
        name = f"word/{kind}s.xml"
        if name in archive.namelist():
            xml = archive.read(name).decode("utf-8")
            for id, inside in re.findall(rf'<w:{kind} w:id="(\d+)">(.*?)</w:{kind}>', xml, re.S):
                words = re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", inside)
                notes[kind, id] = html.unescape("".join(words)).strip()
    order = []
    lines = []
    document = archive.read("word/document.xml").decode("utf-8")
    for paragraph in re.findall(r"<w:p\b[^>]*>(?:(?!<w:p\b).)*?</w:p>", document, re.S):
        line = ""
        pieces = r'<w:t(?: [^>]*)?>([^<]*)</w:t>|<w:(endnote|footnote)Reference\b[^>]*w:id="(\d+)"'
        for piece in re.finditer(pieces, paragraph):
            if piece.group(1) is not None:
                line += html.unescape(piece.group(1))
            else:
                order.append((piece.group(2), piece.group(3)))
                line += f"[^{len(order)}]"
        lines += [line, ""]
    for number, key in enumerate(order, 1):
        lines += [f"[^{number}]: {notes.get(key, '')}", ""]
    text = "\n".join(lines)
if "-o" in args:
    with open(args[args.index("-o") + 1], "w", encoding="utf-8") as file:
        file.write(text)
else:
    sys.stdout.buffer.write(text.encode("utf-8"))
'''

GIT = r'''
import json, os, sys, time

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "control.json")) as file:
    control = json.load(file)
args = sys.argv[1:]
with open(os.path.join(here, "calls.jsonl"), "a") as file:
    file.write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")

if control.get("hang"):
    time.sleep(60)
if control.get("not_a_repository"):
    print("fatal: not a git repository (or any of the parent directories): .git", file=sys.stderr)
    sys.exit(128)
folder, command = args[1], args[2]
if command == "show":
    revision, _, path = args[3].partition(":")
    served = control.get("files", {}).get(revision)
    if served is None:
        print(f"fatal: invalid object name '{revision}'.", file=sys.stderr)
        sys.exit(128)
    with open(served, "rb") as file:
        sys.stdout.buffer.write(file.read())
elif command == "log":
    revision = args[-1]
    line = control.get("log", {}).get(revision)
    if line is None:
        print(f"fatal: bad revision '{revision}'", file=sys.stderr)
        sys.exit(128)
    print(line)
else:
    print("stub git: unexpected arguments", args, file=sys.stderr)
    sys.exit(64)
'''


# The three programs that read a PDF. In the tests a "PDF" is a small JSON file:
# {"pages": [text of each page], "images": {"2": {"text": ..., "scores": {"0": 2, "90": 40}}}}
# and a page "image" is the JSON of that page's entry, which the stand-in tesseract reads.
COMMON = r'''
import json, os, sys, time

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "control.json")) as file:
    control = json.load(file)
args = sys.argv[1:]
with open(os.path.join(here, "calls.jsonl"), "a") as file:
    file.write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")


def source(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


# What this run looks like, for the control file to match against: the program's
# name and its arguments.
run = os.path.basename(sys.argv[0]) + " " + " ".join(args)
if any(word in run for word in control.get("hang_on", [])):
    time.sleep(60)
if any(word in run for word in control.get("fail_on", [])):
    print("stand-in: could not read the file", file=sys.stderr)
    sys.exit(1)
if any(word in run for word in control.get("silent_on", [])):
    sys.exit(0)
if any(word in run for word in control.get("garbage_on", [])):
    sys.stdout.buffer.write(b"\xff\xfe not text at all, and well over eighty bytes of it:" + b" x" * 60 + b"\f")
    sys.exit(0)
'''

PDFTOTEXT = COMMON + r'''
pages = source(args[1])["pages"]            # pdftotext -layout FILE -
sys.stdout.write("".join(page + "\f" for page in pages))
'''

PDFTOPPM = COMMON + r'''
# pdftoppm -f N -l N -scale-to S -gray -png FILE PREFIX
number = args[args.index("-f") + 1]
image = source(args[-2]).get("images", {}).get(number)
if image is not None:
    with open(f"{args[-1]}-{int(number):02d}.png", "w", encoding="utf-8") as file:
        json.dump(dict(image, page=int(number)), file)
'''

TESSERACT = COMMON + r'''
image = source(args[0])                     # tesseract IMAGE - [tsv]
turned = str(image.get("turned", 0))
if args[-1] == "tsv":
    print("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext")
    for _ in range(image.get("scores", {}).get(turned, 0)):
        print("5\t1\t1\t1\t1\t1\t0\t0\t9\t9\t95\tword")
else:
    sys.stdout.write(image.get("text", "") + (f" [read turned {turned}]" if turned != "0" else ""))
'''


class Stub:
    """A stand-in program in a folder of its own, to be put on PATH."""

    def __init__(self, folder, name, source, **control):
        self.folder = folder
        folder.mkdir(exist_ok=True)
        program = folder / name
        program.write_text(f"#!{sys.executable}\n{source}", encoding="utf-8")
        program.chmod(program.stat().st_mode | stat.S_IXUSR)
        self.control(**control)

    def control(self, **control):
        """Set how the stand-in behaves from now on."""
        (self.folder / "control.json").write_text(json.dumps(control), encoding="utf-8")

    def calls(self):
        """The argument lists it has been run with, in order."""
        log = self.folder / "calls.jsonl"
        if not log.exists():
            return []
        return [json.loads(line)["args"] for line in log.read_text(encoding="utf-8").splitlines()]

    def folders(self):
        """The working directory of each run, in order."""
        log = self.folder / "calls.jsonl"
        return [json.loads(line)["cwd"] for line in log.read_text(encoding="utf-8").splitlines()]


def backlog_stub(folder, **control):
    return Stub(folder, "backlog", BACKLOG, **control)


def pandoc_stub(folder, **control):
    return Stub(folder, "pandoc", PANDOC, **control)


def git_stub(folder, **control):
    return Stub(folder, "git", GIT, **control)


def pdf_stubs(folder, **control):
    """Stand-ins for pdftotext, pdftoppm and tesseract, sharing one folder and log."""
    stub = Stub(folder, "pdftotext", PDFTOTEXT, **control)
    Stub(folder, "pdftoppm", PDFTOPPM, **control)
    Stub(folder, "tesseract", TESSERACT, **control)
    return stub


class FakeImage:
    """What the tests give sources-to-text in place of Pillow's Image: it "turns" a
    stand-in page image by recording the turn in the file it saves."""

    def __init__(self, data, turned=0):
        self.data, self.turned = data, turned

    @classmethod
    def open(cls, path):
        with open(path, encoding="utf-8") as file:
            return cls(json.load(file))

    def rotate(self, angle, expand=False):
        return FakeImage(self.data, (-angle) % 360)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(dict(self.data, turned=self.turned), file)


def backlog_project(folder):
    """An empty Backlog project, as far as file-tickets can tell."""
    (folder / "backlog").mkdir(parents=True)
    (folder / "backlog" / "config.yml").write_text('project_name: "Stub"\n', encoding="utf-8")
    return folder


def only(*stubs):
    """A PATH holding these stand-ins and nothing else."""
    return os.pathsep.join(str(stub.folder) for stub in stubs)
