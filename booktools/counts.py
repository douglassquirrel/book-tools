"""The structure and counts of a save: what a glance at two saves should compare first."""

import hashlib
import re
from datetime import datetime, timezone

from booktools.clock import london

TEXT = re.compile(r"<w:t(?: [^>]*)?>([^<]*)</w:t>")
STRAIGHT = ('"', "'", "&quot;", "&apos;")
MEDIA = "word/media/"


def counts(docx):
    """The counts of one save, a Docx, by name."""
    parts = {info.filename: data for info, data in docx.entries}

    def read(name):
        return parts.get(name, b"").decode("utf-8", "replace")

    core = read("docProps/core.xml")
    document = read("word/document.xml")
    endnotes, footnotes = read("word/endnotes.xml"), read("word/footnotes.xml")
    notes = document + endnotes + footnotes
    body = document.split("<w:body>")[1] if "<w:body>" in document else document
    with open(docx.path, "rb") as file:
        sha = hashlib.sha256(file.read()).hexdigest()[:16]
    text = "".join(TEXT.findall(notes))
    several = []
    for kind, xml in (("endnote", endnotes), ("footnote", footnotes)):
        for id, inside in _notes(kind, xml):
            if len(re.findall(r"<w:p[ >]", inside)) > 1:
                several.append(f"{kind} {id}")
    return {
        "sha256": sha,
        "revision": "".join(re.findall(r"<cp:revision>(.*?)<", core)[:1]),
        "modified": "".join(re.findall(r"<dcterms:modified[^>]*>(.*?)<", core)[:1]),
        "paragraphs": len(re.findall(r"<w:p[ >]", body)),
        "tracked changes": sum(
            len(re.findall(rf"<w:{name}[ >]", notes))
            for name in ("ins", "del", "moveFrom", "moveTo")
        ),
        "trackRevisions": "<w:trackRevisions" in read("word/settings.xml"),
        "comments": document.count("<w:commentReference"),
        "endnote markers": document.count("<w:endnoteReference"),
        "endnotes": len(_notes("endnote", endnotes)),
        "footnote markers": document.count("<w:footnoteReference"),
        "footnotes": len(_notes("footnote", footnotes)),
        "straight quotes": sum(text.count(mark) for mark in STRAIGHT),
        "links in notes": (endnotes + footnotes).count("<w:hyperlink"),
        "highlighted runs": notes.count("<w:highlight "),
        "notes of more than one paragraph": several,
    }


def _notes(kind, xml):
    """(id, content) of each real note of a notes part: not the separators."""
    found = re.findall(rf'<w:{kind} w:id="(\d+)">(.*?)</w:{kind}>', xml, re.S)
    return [(id, inside) for id, inside in found if int(id) > 0]


def structure_lines(old, new, utc=False):
    """The 'Structure and counts' section for two saves."""
    before, after = counts(old), counts(new)
    lines = ["== Structure and counts (old | new)"]
    for name in ("sha256", "revision"):
        lines.append(f"{name}: {before[name]} | {after[name]}")
    zone = "UTC" if utc else "London time"
    lines.append(
        f"modified ({zone}): {_when(before['modified'], utc)} | {_when(after['modified'], utc)}"
    )
    lines.extend(_parts(old, new))
    for name in list(before)[3:]:
        was, now = before[name], after[name]
        if isinstance(was, bool):
            lines.append(f"{name}: {'on' if was else 'off'} | {'on' if now else 'off'}")
        elif isinstance(was, list):
            lines.append(f"{name}: {', '.join(was) or 'none'} | {', '.join(now) or 'none'}")
        else:
            change = f" ({now - was:+d})" if now != was else ""
            lines.append(f"{name}: {was} | {now}{change}")
    return lines


def _when(stamp, utc):
    """A time from core.xml (UTC) as it is to be shown."""
    try:
        moment = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return stamp
    return (moment if utc else london(moment)).strftime("%Y-%m-%d %H:%M")


def _parts(old, new):
    """Which entries differ between two saves, and what became of the pictures."""
    was = {info.filename: data for info, data in old.entries}
    now = {info.filename: data for info, data in new.entries}
    differ = []
    for name in list(now) + [name for name in was if name not in now]:
        if name.startswith(MEDIA) and (name not in was or name not in now):
            continue  # a picture added or removed is told on the media line
        if name not in was:
            differ.append(f"{name} (new only)")
        elif name not in now:
            differ.append(f"{name} (old only)")
        elif was[name] != now[name]:
            differ.append(name)
    old_media = sorted(name[len(MEDIA) :] for name in was if name.startswith(MEDIA))
    new_media = sorted(name[len(MEDIA) :] for name in now if name.startswith(MEDIA))
    if old_media == new_media:
        count = len(old_media)
        media = f"the same {count} file{'' if count == 1 else 's'}" if count else "none"
    else:
        removed = [name for name in old_media if name not in new_media]
        added = [name for name in new_media if name not in old_media]
        media = "; ".join(
            f"{word} {', '.join(names)}"
            for word, names in (("removed", removed), ("added", added))
            if names
        )
    return [f"parts that differ: {', '.join(differ) or 'none'}", f"media: {media}"]
