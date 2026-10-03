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


TYPES = "application/vnd.openxmlformats-officedocument.wordprocessingml"
RELATIONS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE = "http://schemas.openxmlformats.org/package/2006"
# A real picture, one white pixel, so that nothing reading the package chokes on it.
PIXEL = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0fIDATx\x01\x01\x04\x00\xfb\xff\x00\xff\xff\xff\x05\xfe\x02\xfeIfn+\x00\x00\x00\x00IEND\xaeB`\x82'


def sample_parts(body=None):
    """The parts of the sample document, a complete package that Word and pandoc can
    open; `body` replaces its paragraphs if given."""
    paragraphs = "".join(BODY_PARAGRAPHS if body is None else body)
    overrides = "".join(
        f'<Override PartName="/word/{name}.xml" ContentType="{TYPES}.{kind}+xml"/>'
        for name, kind in (
            ("document", "document.main"),
            ("endnotes", "endnotes"),
            ("footnotes", "footnotes"),
            ("styles", "styles"),
            ("settings", "settings"),
        )
    )
    relations = "".join(
        f'<Relationship Id="rId{number}" Type="{RELATIONS}/{name}" Target="{name}.xml"/>'
        for number, name in enumerate(("styles", "settings", "endnotes", "footnotes"), 1)
    )
    return {
        "[Content_Types].xml": DECLARATION
        + f'<Types xmlns="{PACKAGE}/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        + overrides
        + '<Override PartName="/docProps/core.xml"'
        ' ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>',
        "_rels/.rels": DECLARATION
        + f'<Relationships xmlns="{PACKAGE}/relationships">'
        f'<Relationship Id="rId1" Type="{RELATIONS}/officeDocument" Target="word/document.xml"/>'
        f'<Relationship Id="rId2" Type="{PACKAGE}/relationships/metadata/core-properties"'
        ' Target="docProps/core.xml"/></Relationships>',
        "word/document.xml": DECLARATION
        + f"<w:document {W} {R} {W16DU}><w:body>{paragraphs}<w:sectPr/></w:body></w:document>",
        "word/_rels/document.xml.rels": DECLARATION
        + f'<Relationships xmlns="{PACKAGE}/relationships">{relations}</Relationships>',
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
        "word/media/image1.png": PIXEL,
        "docProps/core.xml": DECLARATION + "<cp:coreProperties"
        f' xmlns:cp="{PACKAGE}/metadata/core-properties"'
        ' xmlns:dcterms="http://purl.org/dc/terms/"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><cp:revision>3</cp:revision>'
        '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-10-01T09:00:00Z</dcterms:modified>'
        "</cp:coreProperties>",
    }


def edited_parts():
    """A later save of the sample: a word changed, bold removed from a word, a font name
    dropped, a paragraph's spacing changed, a paragraph added, and a note added before
    the others (so every later note is renumbered)."""
    body = list(BODY_PARAGRAPHS)
    # Word renumbers note ids in document order on saving: the old note 1 becomes 2.
    body[2] = (
        body[2]
        .replace("lit at dusk", "lit at dawn")
        .replace('<w:endnoteReference w:id="1"/>', '<w:endnoteReference w:id="2"/>')
        .replace(
            '<w:r><w:t xml:space="preserve">The lamp',
            '<w:r><w:endnoteReference w:id="1"/></w:r><w:r><w:t xml:space="preserve">The lamp',
        )
    )
    body[3] = body[3].replace("<w:r><w:rPr><w:b/></w:rPr><w:t>large</w:t></w:r>", "<w:r><w:t>large</w:t></w:r>")
    body[5] = body[5].replace('<w:rPr><w:rFonts w:ascii="Times-Roman" w:hAnsi="Times-Roman"/></w:rPr>', "")
    body[6] = body[6].replace('w:line="280"', 'w:line="300"')
    body.insert(7, p("A paragraph added in the later save."))
    body[9] = body[9].replace('<w:endnoteReference w:id="2"/>', '<w:endnoteReference w:id="3"/>')
    parts = sample_parts(body)
    parts["word/endnotes.xml"] = (
        DECLARATION
        + f"<w:endnotes {W}>"
        + separators("endnote")
        + note("endnote", 1, "A note added in the later save.")
        + note("endnote", 2, "Recorded by Trinity House in the station log.")
        + note("endnote", 3, "Ibid.")
        + "</w:endnotes>"
    )
    parts["docProps/core.xml"] = parts["docProps/core.xml"].replace(
        "<cp:revision>3</cp:revision>", "<cp:revision>4</cp:revision>"
    ).replace("2026-10-01T09:00:00Z", "2026-10-02T17:30:00Z")
    return parts


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


def spaced_parts():
    """A document with one of each kind of line spacing, for check-spacing."""
    def spaced(text, spacing="", style="", extra=""):
        properties = (f'<w:pStyle w:val="{style}"/>' if style else "") + spacing
        properties = f"<w:pPr>{properties}</w:pPr>" if properties else ""
        return f"<w:p>{properties}<w:r><w:t>{text}</w:t>{extra}</w:r></w:p>"

    long = "A picture sits in this paragraph, whose text runs on well past ninety characters so that it is cut."
    body = [
        heading(1, "The Lighthouse Ledger"),
        spaced("An ordinary paragraph, double spaced by its style."),
        spaced("Single by its own setting.", '<w:spacing w:line="240" w:lineRule="auto"/>'),
        spaced("One and a half by its style.", style="Quote"),
        spaced(long, '<w:spacing w:line="280" w:lineRule="exact"/>', extra="<w:drawing/>"),
        heading(2, "Chapter 2 has a very long heading that runs past forty-five characters"),
        spaced("Within the tolerance.", '<w:spacing w:line="468" w:lineRule="auto"/>'),
        spaced("At least 24 points.", '<w:spacing w:line="480" w:lineRule="atLeast"/>'),
        spaced("Only space after is set here.", '<w:spacing w:after="120"/>'),
    ]
    parts = sample_parts(body)
    parts["word/styles.xml"] = parts["word/styles.xml"].replace(
        "</w:styles>",
        '<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Block Quote"/>'
        '<w:basedOn w:val="Normal"/><w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr>'
        "</w:style></w:styles>",
    )
    parts["word/endnotes.xml"] = parts["word/endnotes.xml"].replace(
        "<w:p><w:r><w:endnoteRef/></w:r><w:r><w:t xml:space=\"preserve\"> Ibid.",
        '<w:p><w:pPr><w:spacing w:line="240" w:lineRule="auto"/></w:pPr>'
        '<w:r><w:endnoteRef/></w:r><w:r><w:t xml:space="preserve"> Ibid.',
    )
    parts["word/footnotes.xml"] = parts["word/footnotes.xml"].replace(
        "<w:p><w:r><w:footnoteRef/></w:r>",
        '<w:p><w:pPr><w:spacing w:line="200" w:lineRule="exact"/></w:pPr><w:r><w:footnoteRef/></w:r>',
    )
    return parts
