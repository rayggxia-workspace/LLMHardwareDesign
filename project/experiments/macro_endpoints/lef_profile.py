"""Strict, lossless-name LEF 5.8 RECT capture profile for one macro.

This is deliberately not a general LEF parser or a pin-access checker.  Every
accepted statement is represented in the result; unsupported syntax fails the
whole capture.  Coordinates stay in the LEF macro coordinate frame.  In
particular, FOREIGN and ORIGIN never imply a DEF placement or rotation here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
import hashlib
import re


PROFILE = "lef58-single-macro-rect-v1"
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_DBU_VALUES = {100, 200, 400, 800, 1000, 2000, 4000, 8000, 10000, 20000}
_ORIENTATIONS = {"N", "S", "E", "W", "FN", "FS", "FE", "FW"}
_CLASSES = {
    "COVER": {None, "BUMP"},
    "RING": {None},
    "BLOCK": {None, "BLACKBOX", "SOFT"},
    "PAD": {None, "INPUT", "OUTPUT", "INOUT", "POWER", "SPACER", "AREAIO"},
    "CORE": {None, "FEEDTHRU", "TIEHIGH", "TIELOW", "SPACER", "ANTENNACELL", "WELLTAP"},
    "ENDCAP": {"PRE", "POST", "TOPLEFT", "TOPRIGHT", "BOTTOMLEFT", "BOTTOMRIGHT"},
}


class LEFProfileError(ValueError):
    """The input cannot be captured completely by this explicit profile."""

    def __init__(self, message: str, *, source_name: str = "", line: int = 1,
                 code: str = "invalid_profile"):
        self.source_name = source_name
        self.line = line
        self.code = code
        super().__init__(f"{source_name or '<bytes>'}:{line}: [{code}] {message}")


@dataclass(frozen=True)
class _Token:
    text: str
    line: int
    quoted: bool = False


def _lex(text: str, source_name: str) -> list[_Token]:
    """Keep bare identifiers byte-for-byte, including literal backslashes."""
    result = []
    i, line = 0, 1

    def fail(message: str, at: int) -> None:
        raise LEFProfileError(message, source_name=source_name, line=at,
                              code="invalid_lexical_input")

    while i < len(text):
        char = text[i]
        if char in " \t\r\n":
            if char == "\n":
                line += 1
            elif char == "\r" and (i + 1 == len(text) or text[i + 1] != "\n"):
                line += 1
            i += 1
            continue
        if ord(char) < 32 or ord(char) == 127:
            fail("control character outside the capture profile", line)
        if char == "#":
            while i < len(text) and text[i] not in "\r\n":
                if (ord(text[i]) < 32 and text[i] != "\t") or ord(text[i]) == 127:
                    fail("control character in comment", line)
                i += 1
            continue
        if char == ";":
            result.append(_Token(";", line))
            i += 1
            continue
        start, start_line = i, line
        if char == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] in "\r\n" or ord(text[i]) < 32 or ord(text[i]) == 127:
                    fail("multiline/control-containing quoted string is unsupported", start_line)
                if text[i] == "\\":
                    fail("escaped quoted strings are outside the capture profile", start_line)
                i += 1
            if i == len(text):
                fail("unterminated quoted string", start_line)
            result.append(_Token(text[start + 1:i], start_line, True))
            i += 1
            if i < len(text) and text[i] not in " \t\r\n;#":
                fail("quoted string must end at a token boundary", start_line)
            continue
        while i < len(text) and text[i] not in " \t\r\n;":
            if ord(text[i]) < 32 or ord(text[i]) == 127:
                fail("control character in identifier", start_line)
            if text[i] == "\\":
                if i + 1 == len(text) or text[i + 1] in " \t\r\n":
                    fail("dangling/whitespace-escaped identifier is unsupported", start_line)
                if ord(text[i + 1]) < 32 or ord(text[i + 1]) == 127:
                    fail("control character in escaped identifier", start_line)
                i += 2
            else:
                i += 1
        result.append(_Token(text[start:i], start_line))
    return result


class _Parser:
    def __init__(self, text: str, source_name: str):
        self.tokens = _lex(text, source_name)
        self.i = 0
        self.source_name = source_name
        self.eof_line = len(text.splitlines()) or 1
        self.dbu = None
        self.diagnostics = []

    def error(self, message: str, token: _Token | None = None,
              code: str = "invalid_profile") -> None:
        raise LEFProfileError(message, source_name=self.source_name,
                              line=token.line if token else self.eof_line, code=code)

    def peek(self) -> _Token | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def pop(self) -> _Token:
        token = self.peek()
        if token is None:
            self.error("unexpected end of file (truncated declaration or scope)")
        self.i += 1
        return token

    def expect(self, value: str) -> _Token:
        token = self.pop()
        if token.quoted or token.text != value:
            self.error(f"expected {value!r}, found {token.text!r}", token)
        return token

    def name(self) -> _Token:
        token = self.pop()
        if token.quoted or token.text == ";" or not token.text or len(token.text) > 2048:
            self.error("expected a bare identifier of at most 2048 characters", token)
        return token

    def arguments(self) -> list[_Token]:
        values = []
        while True:
            token = self.pop()
            if not token.quoted and token.text == ";":
                return values
            values.append(token)

    def unsupported(self, token: _Token, scope: str) -> None:
        self.error(f"unsupported {scope} statement {token.text!r}; capture is incomplete",
                   token, "unsupported_syntax")

    def number(self, token: _Token) -> tuple[str, Decimal, int]:
        if (token.quoted or len(token.text) > 128 or not _NUMBER.fullmatch(token.text)):
            self.error(f"expected a finite decimal coordinate, found {token.text!r}", token)
        value = Decimal(token.text)
        # Explicit numerical limits prevent extreme exponents from allocating
        # unbounded integers; these are profile limits, not LEF syntax rules.
        exponent = value.as_tuple().exponent
        if abs(exponent) > 100 or abs(value.adjusted()) > 100:
            self.error("coordinate exponent exceeds capture profile range (+/-100)", token)
        if self.dbu is None:
            self.error("DATABASE MICRONS must precede geometry", token)
        with localcontext() as context:
            context.prec = len(value.as_tuple().digits) + abs(exponent) + 16
            scaled = value * Decimal(self.dbu)
            if scaled != scaled.to_integral_value():
                self.error(f"coordinate {token.text!r} is not an integer DBU at {self.dbu}/um",
                           token, "fractional_dbu")
            return token.text, value, int(scaled)

    def coordinates(self, tokens: list[_Token], count: int) -> tuple[list[str], list[int]]:
        if len(tokens) != count:
            self.error(f"expected {count} coordinate values, found {len(tokens)}",
                       tokens[0] if tokens else self.peek())
        values = [self.number(token) for token in tokens]
        return [value[0] for value in values], [value[2] for value in values]

    def parse(self) -> dict:
        header = {"version": None, "dbu_per_micron": None,
                  "busbitchars": None, "dividerchar": None}
        seen = set()
        while self.peek() is not None and self.peek().text != "MACRO":
            keyword = self.pop()
            if keyword.quoted or keyword.text not in {"VERSION", "BUSBITCHARS", "DIVIDERCHAR", "UNITS"}:
                self.unsupported(keyword, "header")
            if keyword.text in seen:
                self.error(f"duplicate {keyword.text} declaration", keyword)
            seen.add(keyword.text)
            if keyword.text == "VERSION":
                token = self.pop()
                if token.quoted or token.text != "5.8":
                    self.error("this capture profile requires explicit VERSION 5.8", token)
                header["version"] = token.text
                self.expect(";")
            elif keyword.text in {"BUSBITCHARS", "DIVIDERCHAR"}:
                token = self.pop()
                required = 2 if keyword.text == "BUSBITCHARS" else 1
                if (not token.quoted or len(token.text) != required
                        or any(char.isspace() for char in token.text)
                        or (required == 2 and token.text[0] == token.text[1])):
                    self.error(f"{keyword.text} requires a quoted {required}-character value", token)
                header[keyword.text.lower()] = token.text
                self.expect(";")
            else:
                self.expect("DATABASE")
                self.expect("MICRONS")
                token = self.pop()
                if (token.quoted or len(token.text) > 5 or not token.text.isascii() or not token.text.isdigit()
                        or int(token.text) not in _DBU_VALUES):
                    self.error("unsupported DATABASE MICRONS factor", token)
                self.dbu = header["dbu_per_micron"] = int(token.text)
                self.expect(";")
                self.expect("END")
                self.expect("UNITS")
        if header["version"] is None or self.dbu is None:
            self.error("profile requires explicit VERSION 5.8 and UNITS DATABASE MICRONS", self.peek())
        opening = self.expect("MACRO")
        macro = self.macro(opening)
        end_library = False
        if self.peek() is not None:
            self.expect("END")
            self.expect("LIBRARY")
            end_library = True
        if self.peek() is not None:
            self.error("trailing input or multiple MACROs are outside the single-macro profile", self.peek())
        self.check_geometry(macro)
        return {"profile": PROFILE, "source_name": self.source_name,
                "header": header, "end_library_explicit": end_library,
                "macro": macro, "diagnostics": self.diagnostics}

    def macro(self, opening: _Token) -> dict:
        name = self.name()
        macro = {"name": name.text, "line": opening.line, "class": None,
                 "origin_um": None, "origin_dbu": None, "origin_explicit": False,
                 "size_um": None, "size_dbu": None, "symmetry": None,
                 "foreign": [], "pins": [], "obstructions": []}
        seen, pin_names, foreign_declarations = set(), set(), set()
        while True:
            keyword = self.pop()
            if keyword.quoted:
                self.unsupported(keyword, "MACRO")
            key = keyword.text
            if key == "END":
                end = self.name()
                if end.text != name.text:
                    self.error(f"MACRO END name {end.text!r} does not match {name.text!r}", end)
                break
            if key == "PIN":
                pin = self.pin(keyword)
                if pin["name"] in pin_names:
                    self.error(f"duplicate PIN name {pin['name']!r}", keyword)
                pin_names.add(pin["name"])
                macro["pins"].append(pin)
                continue
            if key == "OBS":
                macro["obstructions"].append(self.geometry("OBS", len(macro["obstructions"]), keyword))
                continue
            if key == "FOREIGN":
                values = self.arguments()
                if len(values) not in {1, 3, 4}:
                    self.error("FOREIGN requires name, optional x y, and optional orientation", keyword)
                if any(token.quoted or token.text == ";" for token in values):
                    self.error("FOREIGN requires bare tokens", keyword)
                foreign_key = tuple(token.text for token in values)
                if foreign_key in foreign_declarations:
                    self.error("duplicate FOREIGN declaration", keyword)
                foreign_declarations.add(foreign_key)
                point_um, point_dbu, orientation = None, None, None
                if len(values) >= 3:
                    point_um, point_dbu = self.coordinates(values[1:3], 2)
                if len(values) == 4:
                    orientation = values[3].text
                    if orientation not in _ORIENTATIONS:
                        self.error("unsupported FOREIGN orientation", values[3])
                macro["foreign"].append({"name": values[0].text, "point_um": point_um,
                                         "point_dbu": point_dbu, "orientation": orientation,
                                         "line": keyword.line, "tokens": list(foreign_key)})
                continue
            if key not in {"CLASS", "ORIGIN", "SIZE", "SYMMETRY"}:
                self.unsupported(keyword, "MACRO")
            if key in seen:
                self.error(f"duplicate {key} declaration", keyword)
            seen.add(key)
            values = self.arguments()
            if key == "CLASS":
                words = [token.text for token in values]
                if (any(token.quoted for token in values) or len(words) not in {1, 2}
                        or words[0] not in _CLASSES
                        or (words[1] if len(words) == 2 else None) not in _CLASSES[words[0]]):
                    self.error("unsupported MACRO CLASS declaration", keyword)
                macro["class"] = " ".join(words)
            elif key == "ORIGIN":
                macro["origin_um"], macro["origin_dbu"] = self.coordinates(values, 2)
                macro["origin_explicit"] = True
            elif key == "SIZE":
                if len(values) != 3 or values[1].quoted or values[1].text != "BY":
                    self.error("SIZE requires width BY height", keyword)
                raw, dbu = self.coordinates([values[0], values[2]], 2)
                if min(dbu) <= 0:
                    self.error("SIZE dimensions must be positive", keyword)
                macro["size_um"], macro["size_dbu"] = raw, dbu
            else:
                words = [token.text for token in values]
                if (not words or any(token.quoted for token in values)
                        or any(word not in {"X", "Y", "R90"} for word in words)
                        or len(set(words)) != len(words)):
                    self.error("SYMMETRY requires distinct X, Y and/or R90 tokens", keyword)
                macro["symmetry"] = words
        if macro["size_dbu"] is None:
            self.error("single-macro capture profile requires an explicit SIZE", name)
        return macro

    def pin(self, opening: _Token) -> dict:
        name = self.name()
        pin = {"name": name.text, "line": opening.line, "direction": None,
               "output_tristate": False, "use": None, "ports": []}
        seen = set()
        while True:
            keyword = self.pop()
            if keyword.quoted:
                self.unsupported(keyword, "PIN")
            if keyword.text == "END":
                end = self.name()
                if end.text != name.text:
                    self.error(f"PIN END name {end.text!r} does not match {name.text!r}", end)
                break
            if keyword.text == "PORT":
                pin["ports"].append(self.geometry("PORT", len(pin["ports"]), keyword))
                continue
            if keyword.text not in {"DIRECTION", "USE"}:
                self.unsupported(keyword, "PIN")
            if keyword.text in seen:
                self.error(f"duplicate PIN {keyword.text} declaration", keyword)
            seen.add(keyword.text)
            values = self.arguments()
            words = [token.text for token in values]
            if any(token.quoted for token in values):
                self.error("PIN attributes require bare tokens", keyword)
            if keyword.text == "DIRECTION":
                if words == ["OUTPUT", "TRISTATE"]:
                    pin["direction"], pin["output_tristate"] = "OUTPUT", True
                elif len(words) == 1 and words[0] in {"INPUT", "OUTPUT", "INOUT", "FEEDTHRU"}:
                    pin["direction"] = words[0]
                else:
                    self.error("unsupported PIN DIRECTION", keyword)
            else:
                if len(words) != 1 or words[0] not in {"SIGNAL", "ANALOG", "POWER", "GROUND", "CLOCK"}:
                    self.error("unsupported PIN USE", keyword)
                pin["use"] = words[0]
        if not pin["ports"]:
            self.error("PIN without a nonempty PORT is outside the capture profile", name)
        return pin

    def geometry(self, scope: str, index: int, opening: _Token) -> dict:
        result = {"index": index, "line": opening.line, "class": None,
                  "layer_declarations": [], "rects": []}
        layer, layer_token, layer_rects = None, None, 0
        while True:
            keyword = self.pop()
            if keyword.quoted:
                self.unsupported(keyword, scope)
            if keyword.text == "END":
                if layer_token is not None and not layer_rects:
                    self.error("LAYER without a RECT is outside the capture profile", layer_token)
                if not result["rects"]:
                    self.error(f"empty {scope} is outside the capture profile", opening)
                return result
            if keyword.text == "CLASS" and scope == "PORT":
                if result["class"] is not None or layer is not None:
                    self.error("PORT CLASS must appear once before geometry", keyword)
                token = self.pop()
                if token.quoted or token.text not in {"NONE", "CORE", "BUMP"}:
                    self.error("unsupported PORT CLASS", token)
                result["class"] = token.text
                self.expect(";")
            elif keyword.text == "LAYER":
                if layer_token is not None and not layer_rects:
                    self.error("LAYER without a RECT is outside the capture profile", layer_token)
                token = self.name()
                self.expect(";")
                layer, layer_token, layer_rects = token.text, keyword, 0
                result["layer_declarations"].append({"name": layer, "line": keyword.line})
            elif keyword.text == "RECT":
                if layer is None:
                    self.error("RECT must follow a LAYER declaration", keyword)
                values = self.arguments()
                raw, dbu = self.coordinates(values, 4)
                if dbu[0] >= dbu[2] or dbu[1] >= dbu[3]:
                    self.error("RECT must have strictly ordered corners and positive area", keyword)
                result["rects"].append({"layer": layer, "rect_um": raw,
                                         "rect_dbu": dbu, "line": keyword.line})
                layer_rects += 1
            else:
                self.unsupported(keyword, scope)

    def check_geometry(self, macro: dict) -> None:
        nonzero_origin = macro["origin_dbu"] is not None and any(macro["origin_dbu"])
        macro["bbox_check"] = "not_evaluated_nonzero_origin" if nonzero_origin else "raw_size_box"
        if nonzero_origin:
            self.diagnostics.append({"kind": "bbox_check_not_evaluated", "line": macro["line"],
                                     "reason": "nonzero ORIGIN retained; no coordinate transform applied"})
        width, height = macro["size_dbu"]
        groups = []
        for pin in macro["pins"]:
            for attribute in ("direction", "use"):
                if pin[attribute] is None:
                    self.diagnostics.append({"kind": f"missing_pin_{attribute}",
                                             "pin": pin["name"], "line": pin["line"]})
            for port in pin["ports"]:
                groups.append((port, {"scope": "pin_port", "pin": pin["name"],
                                      "port_index": port["index"]}))
        for obstruction in macro["obstructions"]:
            groups.append((obstruction, {"scope": "obstruction", "obs_index": obstruction["index"]}))
        for group, location in groups:
            seen = {}
            for rect in group["rects"]:
                key = (rect["layer"], tuple(rect["rect_dbu"]))
                if key in seen:
                    self.diagnostics.append({"kind": "duplicate_rect", **location,
                                             "line": rect["line"], "first_line": seen[key],
                                             "layer": rect["layer"], "rect_dbu": rect["rect_dbu"][:]})
                else:
                    seen[key] = rect["line"]
                xlo, ylo, xhi, yhi = rect["rect_dbu"]
                if not nonzero_origin and (xlo < 0 or ylo < 0 or xhi > width or yhi > height):
                    self.diagnostics.append({"kind": "outside_macro_size", **location,
                                             "line": rect["line"], "layer": rect["layer"],
                                             "rect_dbu": rect["rect_dbu"][:],
                                             "reference": "raw [0, SIZE] box; omitted ORIGIN uses LEF default zero"})


def parse_lef(data: bytes, source_name: str = "") -> dict:
    """Capture one ASCII LEF macro; reject any unrepresented input syntax.

    Missing ORIGIN, SYMMETRY, CLASS, BUSBITCHARS and DIVIDERCHAR stay ``None``;
    pin DIRECTION/USE omissions are also kept and diagnosed.  VERSION, explicit
    UNITS/DATABASE, SIZE and nonempty geometric PORTs are profile requirements.
    Integer DBU conversion is exact, while original coordinate spellings remain
    strings.  Duplicate/outside rectangles are retained with diagnostics.
    """
    if not isinstance(data, bytes):
        raise TypeError("parse_lef expects bytes")
    if not isinstance(source_name, str):
        raise TypeError("source_name must be a string")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        line = data[:error.start].count(b"\n") + 1
        raise LEFProfileError("non-ASCII input is outside the capture profile",
                              source_name=source_name, line=line,
                              code="invalid_lexical_input") from error
    result = _Parser(text, source_name).parse()
    result["source_sha256"] = hashlib.sha256(data).hexdigest()
    return result
