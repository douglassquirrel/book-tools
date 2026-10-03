"""The line spacing each paragraph really has, through Word's chain of style inheritance."""

from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TOLERANCE = 12  # 240ths of a line either side of the expected spacing


def own_spacing(properties):
    """The line and lineRule set in a <w:pPr> element itself, if any."""
    if properties is None:
        return {}
    spacing = properties.find(W + "spacing")
    if spacing is None:
        return {}
    wanted = (W + "line", W + "lineRule")
    return {key[len(W) :]: value for key, value in spacing.attrib.items() if key in wanted}


class Styles:
    """The spacing each paragraph style gives, read from a document's styles part."""

    def __init__(self, styles_xml):
        root = ElementTree.fromstring(styles_xml.encode("utf-8"))
        self._styles = {}  # id -> (the id it is based on, its own spacing, its name)
        self.default = "Normal"
        defaults = []
        for style in root.iter(W + "style"):
            if style.get(W + "type") != "paragraph":
                continue
            id = style.get(W + "styleId")
            based_on, name = style.find(W + "basedOn"), style.find(W + "name")
            self._styles[id] = (
                based_on.get(W + "val") if based_on is not None else None,
                own_spacing(style.find(W + "pPr")),
                name.get(W + "val") if name is not None else id,
            )
            if style.get(W + "default") == "1":
                defaults.append(id)
        if defaults:
            self.default = defaults[0]
        document = root.find(W + "docDefaults")
        self._base = {}
        if document is not None:
            self._base = own_spacing(document.find(W + "pPrDefault/" + W + "pPr"))

    def spacing(self, style_id, seen=()):
        """The {"line": ..., "lineRule": ...} a style gives, through what it is based on
        and the document defaults; either key may be missing."""
        if style_id is None or style_id not in self._styles or style_id in seen:
            return dict(self._base)
        based_on, own, _ = self._styles[style_id]
        result = self.spacing(based_on, seen + (style_id,))
        result.update(own)
        return result

    def name(self, style_id):
        return self._styles.get(style_id, (None, None, style_id))[2]


def describe(spacing, expect=480):
    """(the spacing in words, whether it is the expected spacing) for a paragraph whose
    effective spacing is the dict `spacing`."""
    line = spacing.get("line")
    rule = spacing.get("lineRule", "auto")
    if line is None:
        # Nothing set anywhere: Word shows single spacing.
        return "single (unset)", abs(240 - expect) <= TOLERANCE
    value = int(line)
    if rule == "auto":
        return f"{value / 240:g} lines", abs(value - expect) <= TOLERANCE
    return f"{rule} {value / 20:g} pt", False
