import pytest

from booktools.spacing import Styles, describe
from tests.samples import W

pytestmark = pytest.mark.tier1


def styles(*definitions, defaults='<w:spacing w:line="240" w:lineRule="auto"/>'):
    return Styles(
        f"<w:styles {W}><w:docDefaults><w:pPrDefault><w:pPr>{defaults}</w:pPr></w:pPrDefault>"
        "</w:docDefaults>" + "".join(definitions) + "</w:styles>"
    )


def style(id, based_on=None, spacing="", default=False, type="paragraph"):
    return (
        f'<w:style w:type="{type}"' + (' w:default="1"' if default else "") + f' w:styleId="{id}">'
        f'<w:name w:val="{id} name"/>'
        + (f'<w:basedOn w:val="{based_on}"/>' if based_on else "")
        + (f"<w:pPr>{spacing}</w:pPr>" if spacing else "")
        + "</w:style>"
    )


CHAIN = (
    style("Normal", spacing='<w:spacing w:line="480" w:lineRule="auto"/>', default=True),
    style("Body", based_on="Normal"),
    style("Quote", based_on="Body", spacing='<w:spacing w:after="120"/>'),
    style("Tight", based_on="Quote", spacing='<w:spacing w:line="280" w:lineRule="exact"/>'),
    style("Loop", based_on="Loop"),
    style("Emphasis", spacing='<w:spacing w:line="999"/>', type="character"),
)


def test_spacing_is_inherited_through_a_chain_of_styles_three_deep():
    s = styles(*CHAIN)
    assert s.spacing("Quote") == {"line": "480", "lineRule": "auto"}
    assert s.spacing("Tight") == {"line": "280", "lineRule": "exact"}
    assert (s.default, s.name("Quote")) == ("Normal", "Quote name")


def test_a_style_that_sets_nothing_falls_back_to_the_document_defaults():
    s = styles(style("Plain", default=True))
    assert s.spacing("Plain") == {"line": "240", "lineRule": "auto"}
    assert styles(style("Plain"), defaults="").spacing("Plain") == {}


def test_an_unknown_style_a_character_style_and_a_style_based_on_itself_do_not_break_it():
    s = styles(*CHAIN)
    assert s.spacing("NoSuchStyle") == {"line": "240", "lineRule": "auto"}
    assert s.spacing("Emphasis") == {"line": "240", "lineRule": "auto"}
    assert s.spacing("Loop") == {"line": "240", "lineRule": "auto"}
    assert s.name("NoSuchStyle") == "NoSuchStyle"


def test_double_spacing_is_480_give_or_take_12():
    for line, ok in (("480", True), ("468", True), ("492", True), ("467", False), ("493", False)):
        assert describe({"line": line, "lineRule": "auto"})[1] is ok
    assert describe({"line": "480", "lineRule": "auto"}) == ("2 lines", True)
    assert describe({"line": "360"}) == ("1.5 lines", False)  # no rule given means auto


def test_exact_and_at_least_never_match_and_are_given_in_points():
    assert describe({"line": "280", "lineRule": "exact"}) == ("exact 14 pt", False)
    assert describe({"line": "480", "lineRule": "atLeast"}) == ("atLeast 24 pt", False)
    assert describe({"line": "240", "lineRule": "exact"}, expect=240) == ("exact 12 pt", False)


def test_a_paragraph_with_no_spacing_anywhere_counts_as_single():
    assert describe({}) == ("single (unset)", False)
    assert describe({}, expect=240) == ("single (unset)", True)
    assert describe({"line": "240", "lineRule": "auto"}, expect=240) == ("1 lines", True)
    assert describe({"line": "480", "lineRule": "auto"}, expect=240) == ("2 lines", False)
    assert describe({"line": "360", "lineRule": "auto"}, expect=360) == ("1.5 lines", True)
