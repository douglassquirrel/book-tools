import pytest

from booktools.xmlscan import paragraph_spans

pytestmark = pytest.mark.tier1


def slices(xml):
    return [(xml[s:e], depth) for s, e, depth in paragraph_spans(xml)]


def test_finds_each_paragraph_and_is_not_fooled_by_paragraph_properties():
    one = '<w:p w:rsidR="00A1"><w:pPr><w:pStyle w:val="Body"/></w:pPr><w:r><w:t>One</w:t></w:r></w:p>'
    two = "<w:p><w:r><w:t>Two</w:t></w:r></w:p>"
    xml = "<w:body>" + one + two + "<w:sectPr/></w:body>"
    assert slices(xml) == [(one, 1), (two, 1)]


def test_counts_an_empty_self_closing_paragraph():
    xml = "<w:body><w:p/><w:p><w:r><w:t>x</w:t></w:r></w:p></w:body>"
    assert slices(xml) == [("<w:p/>", 1), ("<w:p><w:r><w:t>x</w:t></w:r></w:p>", 1)]


def test_reports_a_paragraph_inside_a_paragraph_at_depth_two():
    inner = "<w:p><w:r><w:t>in the box</w:t></w:r></w:p>"
    outer = (
        "<w:p><w:r><w:drawing><w:txbxContent>" + inner + "</w:txbxContent></w:drawing></w:r></w:p>"
    )
    assert slices("<w:body>" + outer + "</w:body>") == [(outer, 1), (inner, 2)]


def test_parse_gives_each_element_its_offsets_and_children():
    from booktools.xmlscan import parse

    xml = '<w:r w:rsidR="00A1"><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">a &gt; b</w:t></w:r>'
    run = parse(xml)
    assert (run.name, run.attrs, xml[run.start : run.end]) == ("w:r", ' w:rsidR="00A1"', xml)
    assert [c.name for c in run.children] == ["w:rPr", "w:t"]
    rpr, t = run.children
    assert xml[rpr.start : rpr.end] == "<w:rPr><w:b/></w:rPr>"
    assert [c.name for c in rpr.children] == ["w:b"]
    assert xml[t.open_end : t.close_start] == "a &gt; b"
    assert xml[run.open_end : run.close_start] == xml[len('<w:r w:rsidR="00A1">') : -len("</w:r>")]
