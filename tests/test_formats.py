import pytest

from booktools.formats import paragraphs, signature

pytestmark = pytest.mark.tier1


def test_the_signature_lists_what_is_on_in_a_fixed_order():
    rpr = (
        '<w:rPr><w:rFonts w:ascii="Times-Roman" w:hAnsi="Arial"/><w:i/><w:b/>'
        '<w:color w:val="FF0000"/><w:sz w:val="24"/><w:rStyle w:val="Emphasis"/>'
        '<w:highlight w:val="yellow"/><w:vertAlign w:val="superscript"/>'
        "<w:smallCaps/><w:caps/><w:strike/><w:u w:val=\"single\"/><w:vanish/></w:rPr>"
    )
    assert signature(rpr) == (
        "b,i,u,strike,caps,smallCaps,vanish,sz=24,vertAlign=superscript,highlight=yellow,"
        "color=FF0000,rStyle=Emphasis,font=Times-Roman"
    )
    assert signature("") == ""


def test_a_toggle_switched_off_is_not_in_the_signature():
    assert signature('<w:rPr><w:b w:val="0"/><w:i w:val="false"/><w:u w:val="none"/></w:rPr>') == ""
    assert signature('<w:rPr><w:b w:val="1"/><w:i w:val="true"/></w:rPr>') == "b,i"


def test_each_character_of_a_paragraph_carries_its_run_s_formatting():
    xml = (
        "<w:body>"
        '<w:p w:rsidR="00A1"><w:pPr><w:pStyle w:val="Quote"/><w:rPr><w:b/></w:rPr></w:pPr>'
        "<w:r><w:t>a&amp;</w:t></w:r>"
        "<w:r><w:rPr><w:i/></w:rPr><w:t>b</w:t><w:tab/><w:endnoteReference w:id=\"3\"/></w:r>"
        "</w:p>"
        "<w:p><w:r><w:br/><w:drawing>x</w:drawing><w:sym w:char=\"F0A7\"/><w:footnoteReference w:id=\"1\"/></w:r></w:p>"
        "</w:body>"
    )
    first, second = paragraphs(xml)
    assert first == (
        '<w:pPr><w:pStyle w:val="Quote"/></w:pPr>',  # the paragraph mark's formatting is left out
        [("a", ""), ("&", ""), ("b", "i")]
        + [(c, "i") for c in "{tab}"]
        + [(c, "i") for c in "{endnoteReference}"],
    )
    assert second[0] == ""
    assert "".join(c for c, _ in second[1]) == "{br}{drawing}{sym}{footnoteReference}"


def test_revision_ids_in_paragraph_properties_are_left_out():
    xml = (
        '<w:p><w:pPr><w:spacing w:line="480"/><w:sectPr w:rsidR="00A1" w:rsidSect="00B2">'
        '<w:pgSz w:w="1"/></w:sectPr></w:pPr><w:r><w:t>x</w:t></w:r></w:p>'
    )
    assert paragraphs(xml)[0][0] == (
        '<w:pPr><w:spacing w:line="480"/><w:sectPr><w:pgSz w:w="1"/></w:sectPr></w:pPr>'
    )


def test_paragraphs_are_found_as_the_source_script_found_them():
    # An empty self-closing paragraph is not counted, and of a paragraph holding a
    # text box only the paragraphs inside the box are.
    xml = (
        "<w:p/><w:p><w:r><w:t>one</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>outer</w:t></w:r><w:r><w:drawing><w:txbxContent>"
        "<w:p><w:r><w:t>boxed</w:t></w:r></w:p></w:txbxContent></w:drawing></w:r></w:p>"
    )
    assert ["".join(c for c, _ in chars) for _, chars in paragraphs(xml)] == ["one", "boxed"]
