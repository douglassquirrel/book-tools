"""The pieces of turning a source PDF into searchable text, page by page."""

READS_WELL = 150  # a page scoring this or more as it stands is not tried turned
TURNS = (90, 180, 270)


def split_pages(text):
    """The pages of what `pdftotext -layout` printed for a PDF."""
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def needs_ocr(page, min_chars=80):
    """Whether a page has so little text that it should be read from its image."""
    return len("".join(page.split())) < min_chars


def page_header(number, total, ocr=False, turned=0):
    """The line that heads a page's block of text."""
    how = ""
    if ocr:
        how = f" (OCR, page turned {turned}° clockwise)" if turned else " (OCR)"
    return f"=== PDF page {number} of {total}{how} ==="


def assemble(pages, ocr, turned):
    """The whole text of a converted PDF: each page under its header."""
    total = len(pages)
    return "".join(
        f"\n{page_header(number, total, ocr[number - 1], turned[number - 1])}\n{page}"
        for number, page in enumerate(pages, 1)
    )


def score(tsv):
    """How well Tesseract read a page, from its TSV output: the number of words of
    four or more letters read with confidence 80 or more."""
    count = 0
    for line in tsv.splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) != 12:
            continue
        word = fields[11].strip()
        if word.isalpha() and len(word) >= 4 and float(fields[10]) >= 80:
            count += 1
    return count


def best_turn(scores):
    """Which clockwise turn (0, 90, 180 or 270) to read a page at, from {turn: score}.
    `scores` holds only 0 when the page reads well enough as it is."""
    best, turn = scores[0], 0
    if best < READS_WELL:
        for candidate in TURNS:
            found = scores.get(candidate, 0)
            # Clearly better: more than half as many again, and at least three more.
            if found > best * 1.5 and found >= best + 3:
                best, turn = found, candidate
    return turn
