"""A paragraph as a sequence of characters, each with its formatting: the method of
comparing two saves character by character and format by format."""

import html
import re

TOGGLES = ("b", "i", "u", "strike", "caps", "smallCaps", "vanish")
VALUES = ("sz", "vertAlign", "highlight", "color", "rStyle")
OFF = ("0", "false", "none")
# Innermost paragraphs only; an empty <w:p/> is not one.
PARAGRAPH = re.compile(r"<w:p\b[^>]*>(?:(?!<w:p\b).)*?</w:p>", re.S)
RUN = re.compile(r"<w:r\b[^>]*>(?:(?!</w:r>).)*?</w:r>", re.S)
CONTENT = re.compile(
    r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>"
    r"|<w:(tab|br|endnoteReference|footnoteReference|drawing|sym)\b[^>]*>"
)


def signature(rpr):
    """The formatting of a run, from its <w:rPr> text, as one comparable string."""
    out = []
    for tag in TOGGLES:
        found = re.search(rf'<w:{tag}(?: w:val="([^"]*)")?/>', rpr)
        if found and found.group(1) not in OFF:
            out.append(tag)
    for tag in VALUES:
        found = re.search(rf'<w:{tag} w:val="([^"]*)"/>', rpr)
        if found:
            out.append(f"{tag}={found.group(1)}")
    found = re.search(r'<w:rFonts [^>]*w:ascii="([^"]*)"', rpr)
    if found:
        out.append("font=" + found.group(1))
    return ",".join(out)


def paragraphs(xml):
    """For each paragraph of a part: (its properties, its characters), the characters
    being (character, formatting signature) pairs."""
    result = []
    for paragraph in PARAGRAPH.findall(xml):
        found = re.search(r"<w:pPr>.*?</w:pPr>", paragraph, re.S)
        properties = found.group(0) if found else ""
        # The formatting of the paragraph mark and revision ids are not compared.
        properties = re.sub(r"<w:rPr>.*?</w:rPr>", "", properties, flags=re.S)
        properties = re.sub(r'\s+w:rsid\w*="[^"]*"', "", properties)
        chars = []
        for run in RUN.findall(paragraph):
            rpr = re.search(r"<w:rPr>.*?</w:rPr>", run, re.S)
            formatting = signature(rpr.group(0) if rpr else "")
            for content in CONTENT.finditer(run):
                if content.group(1) is not None:
                    text = html.unescape(content.group(1))
                else:
                    text = "{" + content.group(2) + "}"
                chars.extend((char, formatting) for char in text)
        result.append((properties, chars))
    return result
