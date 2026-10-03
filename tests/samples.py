"""A small invented manuscript, as the parts of a .docx. Every test document starts here."""

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
W16DU = 'xmlns:w16du="http://schemas.microsoft.com/office/word/2023/wordml/word16du"'
DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'


def p(text):
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def heading(level, text):
    return (
        f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'
    )


BODY_PARAGRAPHS = [
    heading(1, "The Lighthouse Ledger"),
    heading(2, "Chapter 1"),
    # One sentence that Word has split across two runs, with an endnote.
    '<w:p><w:r><w:t xml:space="preserve">The lamp was lit at dusk, and the kee</w:t></w:r>'
    '<w:proofErr w:type="spellStart"/><w:r><w:t>per isn’t one to waste oil.</w:t></w:r>'
    '<w:r><w:rPr><w:rStyle w:val="EndnoteReference"/></w:rPr><w:endnoteReference w:id="1"/></w:r>'
    "</w:p>",
    # Italic and bold words in mid-sentence, with a footnote.
    '<w:p><w:r><w:t xml:space="preserve">She wrote </w:t></w:r>'
    "<w:r><w:rPr><w:i/></w:rPr><w:t>every</w:t></w:r>"
    '<w:r><w:t xml:space="preserve"> figure in a </w:t></w:r>'
    "<w:r><w:rPr><w:b/></w:rPr><w:t>large</w:t></w:r>"
    '<w:r><w:t xml:space="preserve"> ledger.</w:t></w:r>'
    '<w:r><w:footnoteReference w:id="1"/></w:r></w:p>',
    "<w:tbl><w:tr><w:tc>" + p("Oil used: 12 pints") + "</w:tc></w:tr></w:tbl>",
    '<w:p><w:r><w:rPr><w:rFonts w:ascii="Times-Roman" w:hAnsi="Times-Roman"/></w:rPr>'
    "<w:t>A caption set in another font.</w:t></w:r></w:p>",
    '<w:p><w:pPr><w:spacing w:line="280" w:lineRule="exact"/></w:pPr>'
    "<w:r><w:t>A line at exact spacing.</w:t></w:r></w:p>",
    heading(2, "Chapter 2"),
    "<w:p><w:r><w:t>The log for March is missing.</w:t></w:r>"
    '<w:r><w:endnoteReference w:id="2"/></w:r></w:p>',
]


def separators(kind):
    return (
        f'<w:{kind} w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:{kind}>'
        f'<w:{kind} w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/>'
        f"</w:r></w:p></w:{kind}>"
    )


def note(kind, id, text):
    return (
        f'<w:{kind} w:id="{id}"><w:p><w:r><w:{kind}Ref/></w:r>'
        f'<w:r><w:t xml:space="preserve"> {text}</w:t></w:r></w:p></w:{kind}>'
    )


def sample_parts(body=None):
    """The parts of the sample document; `body` replaces its paragraphs if given."""
    paragraphs = "".join(BODY_PARAGRAPHS if body is None else body)
    return {
        "[Content_Types].xml": DECLARATION + "<Types"
        ' xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        "_rels/.rels": DECLARATION + "<Relationships"
        ' xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        "word/document.xml": DECLARATION
        + f"<w:document {W} {R} {W16DU}><w:body>{paragraphs}<w:sectPr/></w:body></w:document>",
        "word/endnotes.xml": DECLARATION
        + f"<w:endnotes {W}>"
        + separators("endnote")
        + note("endnote", 1, "Recorded by Trinity House in the station log.")
        + note("endnote", 2, "Ibid.")
        + "</w:endnotes>",
        "word/footnotes.xml": DECLARATION
        + f"<w:footnotes {W}>"
        + separators("footnote")
        + note("footnote", 1, "Imperial pints.")
        + "</w:footnotes>",
        "word/styles.xml": DECLARATION
        + f"<w:styles {W}>"
        '<w:docDefaults><w:pPrDefault><w:pPr><w:spacing w:line="240" w:lineRule="auto"/></w:pPr>'
        "</w:pPrDefault></w:docDefaults>"
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
        '<w:pPr><w:spacing w:line="480" w:lineRule="auto"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
        '<w:basedOn w:val="Normal"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>'
        '<w:basedOn w:val="Heading1"/></w:style>'
        "</w:styles>",
        "word/settings.xml": DECLARATION + f"<w:settings {W}/>",
        "word/media/image1.png": b"\x89PNG\r\n\x1a\n not really a picture",
        "docProps/core.xml": DECLARATION + "<cp:coreProperties"
        ' xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
        ' xmlns:dcterms="http://purl.org/dc/terms/"><cp:revision>3</cp:revision>'
        "<dcterms:modified>2026-10-01T09:00:00Z</dcterms:modified></cp:coreProperties>",
    }


SAMPLE_EDITS = [
    {
        "id": "E1",
        "find": "keeper isn’t one",
        "replace": "keeper is not one",
        "why": "no contractions",
    },
    {"id": "E2", "find": "large ledger", "replace": "ledger", "why": "cut"},
    {
        "id": "E3",
        "where": "endnote:1",
        "find": "Trinity House",
        "replace": "Trinity House, London",
        "why": "place",
    },
]
