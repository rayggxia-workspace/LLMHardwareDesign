"""ASCII Liberty syntax capture and a strict single-cell interface profile.

The generic syntax tree consumes the entire input, including timing tables.
Only interface declarations are interpreted.  Timing syntax capture does not
qualify timing arcs, electrical values, routing access, or a hard macro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import hashlib
import re


PROFILE = "liberty-single-cell-interface-v1"
AREA_SEMICOLON_COMPAT_PROFILE = "liberty-single-cell-interface-area-semicolon-compat-v1"
MAX_BITS = 65536
_IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
_INTEGER = re.compile(r"[0-9]+\Z")
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_BIT_NAME = re.compile(r"([^\[\]\\\s]+)\[(0|[1-9][0-9]*)(?::(0|[1-9][0-9]*))?\]\Z")
_DIRECTIONS = {"input", "output", "inout", "internal"}
_NUMERIC_FIELDS = {"capacitance", "rise_capacitance", "fall_capacitance", "max_capacitance",
                   "min_capacitance", "max_transition", "min_transition", "max_fanout",
                   "min_fanout", "fanout_load", "min_pulse_width_high", "min_pulse_width_low"}
_PIN_FIELDS = _NUMERIC_FIELDS | {
    "direction", "clock", "function", "three_state", "driver_type", "signal_type",
    "related_power_pin", "related_ground_pin", "pg_type", "voltage_name",
    "physical_connection", "internal_node", "connection_class", "always_on", "is_pad",
    "nextstate_type", "power_down_function", "clamp_0_function", "clamp_1_function",
    "alive_during_power_up", "alive_during_partial_power_down", "antenna_diode_type",
    "is_clock_gating_clock_pin", "is_clock_gating_enable_pin", "is_clock_gating_test_pin",
    "is_clock_gating_out_pin", "is_isolation_cell_data_pin", "is_isolation_cell_enable_pin",
    "is_level_shifter_data_pin", "is_level_shifter_enable_pin",
}
_PIN_COMPLEX = {"capacitance_range", "rise_capacitance_range", "fall_capacitance_range"}
_PIN_GROUPS = {"timing", "internal_power", "receiver_capacitance", "char_config",
               "ccsn_first_stage", "ccsn_last_stage"}
_PG_TYPES = {"primary_power", "primary_ground", "backup_power", "backup_ground",
             "internal_power", "internal_ground", "nwell", "pwell", "deepnwell", "deeppwell"}
_CELL_GROUPS = {"bus", "pin", "pg_pin", "leakage_power", "internal_power", "ff", "ff_bank",
                "latch", "latch_bank", "statetable", "mode_definition", "char_config",
                "dynamic_current", "intrinsic_parasitic", "generated_clock", "test_cell"}


class LibertyProfileError(ValueError):
    def __init__(self, message, *, source_name="", line=1, code="invalid_profile"):
        self.source_name, self.line, self.code = source_name, line, code
        super().__init__(f"{source_name or '<bytes>'}:{line}: [{code}] {message}")


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    raw: str
    line: int
    start: int
    end: int


@dataclass
class _Value:
    raw: str
    tokens: list[_Token]
    line: int

    @property
    def scalar(self):
        if len(self.tokens) == 1 and self.tokens[0].kind in {"word", "string"}:
            return self.tokens[0].value
        return None

    def public(self):
        return {"raw": self.raw, "value": self.scalar, "line": self.line}


@dataclass
class _Node:
    kind: str
    name: str
    line: int
    start: int
    end: int
    end_line: int
    args: list[_Value] = field(default_factory=list)
    value: _Value | None = None
    children: list[_Node] = field(default_factory=list)
    trailing_semicolon: bool = False
    missing_semicolon_compatibility: bool = False

    def public(self):
        node = {"kind": self.kind, "name": self.name, "line": self.line,
                "end_line": self.end_line, "start": self.start, "end": self.end}
        if self.value is not None:
            node["value"] = self.value.public()
        else:
            node["args"] = [value.public() for value in self.args]
        if self.kind == "group":
            node["children"] = [child.public() for child in self.children]
            node["trailing_semicolon"] = self.trailing_semicolon
        if self.missing_semicolon_compatibility:
            node["terminator"] = "missing_semicolon_compatibility"
        return node


def _lex(text, source_name):
    tokens = []
    i, line = 0, 1

    def fail(message, at=None):
        raise LibertyProfileError(message, source_name=source_name,
                                  line=line if at is None else at, code="lexical_error")

    def newline_at(index):
        if text.startswith("\r\n", index):
            return 2
        return 1 if index < len(text) and text[index] in "\r\n" else 0

    while i < len(text):
        char = text[i]
        if char in " \t\r\n":
            count = newline_at(i)
            if count:
                line += 1
                i += count
            else:
                i += 1
            continue
        if char == "\\" and newline_at(i + 1):
            i += 1 + newline_at(i + 1)
            line += 1
            continue
        if text.startswith("//", i):
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        if text.startswith("/*", i):
            opening = line
            i += 2
            while i < len(text) and not text.startswith("*/", i):
                if text.startswith("/*", i):
                    fail("nested block comments are outside the profile", opening)
                count = newline_at(i)
                if count:
                    line += 1
                    i += count
                else:
                    i += 1
            if i == len(text):
                fail("unterminated block comment", opening)
            i += 2
            continue
        start, opening = i, line
        if char in "(){}:;,":
            tokens.append(_Token(char, char, char, line, i, i + 1))
            i += 1
            continue
        if char == '"':
            i += 1
            logical = []
            while i < len(text) and text[i] != '"':
                if text[i] == "\\":
                    if i + 1 == len(text):
                        fail("dangling escape in quoted string", opening)
                    count = newline_at(i + 1)
                    if count:
                        i += count + 1
                        line += 1
                    else:
                        # Keep literal escape spelling; never merge differently
                        # escaped interface identifiers through unescaping.
                        logical.append(text[i:i + 2])
                        i += 2
                else:
                    count = newline_at(i)
                    if count:
                        logical.append(text[i:i + count])
                        i += count
                        line += 1
                    else:
                        logical.append(text[i])
                        i += 1
            if i == len(text):
                fail("unterminated quoted string", opening)
            i += 1
            tokens.append(_Token("string", "".join(logical), text[start:i], opening, start, i))
            continue
        logical, brackets = [], 0
        while i < len(text):
            char = text[i]
            if char == "\\":
                if i + 1 == len(text):
                    fail("dangling escape in bare token", opening)
                count = newline_at(i + 1)
                if count:
                    i += count + 1
                    line += 1
                elif text[i + 1] in " \t":
                    fail("escaped whitespace in bare identifier is outside the profile", opening)
                else:
                    logical.append(text[i:i + 2])
                    i += 2
                continue
            if char in " \t\r\n(){};,\"" or (char == ":" and not brackets):
                break
            if text.startswith("/*", i) or text.startswith("//", i):
                break
            if char == "[":
                brackets += 1
            elif char == "]":
                brackets -= 1
                if brackets < 0:
                    fail("unmatched bracket in bare token", opening)
            logical.append(char)
            i += 1
        if brackets:
            fail("unclosed bracket in bare token", opening)
        if i == start:
            fail(f"unexpected character {text[i]!r}")
        tokens.append(_Token("word", "".join(logical), text[start:i], opening, start, i))
    return tokens


class _Syntax:
    def __init__(self, text, source_name, profile=PROFILE):
        self.text, self.source_name = text, source_name
        self.profile, self.diagnostics = profile, []
        self.tokens = _lex(text, source_name)
        self.i, self.eof_line = 0, len(text.splitlines()) or 1

    def error(self, message, token=None, code="syntax_error"):
        raise LibertyProfileError(message, source_name=self.source_name,
                                  line=token.line if token else self.eof_line, code=code)

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def pop(self):
        token = self.peek()
        if token is None:
            self.error("unexpected end of input; truncated statement or group")
        self.i += 1
        return token

    def expect(self, kind):
        token = self.pop()
        if token.kind != kind:
            self.error(f"expected {kind!r}, found {token.raw!r}", token)
        return token

    def make_value(self, tokens):
        if not tokens:
            self.error("empty attribute value or argument", self.peek())
        return _Value(self.text[tokens[0].start:tokens[-1].end], tokens, tokens[0].line)

    def arguments(self):
        self.expect("(")
        if self.peek() is not None and self.peek().kind == ")":
            self.pop()
            return []
        result, current, depth = [], [], 0
        while True:
            token = self.pop()
            if token.kind in {"{", "}", ";"}:
                self.error("unterminated parenthesized argument list", token)
            if token.kind == "(":
                depth += 1
            elif token.kind == ")":
                if depth == 0:
                    result.append(self.make_value(current))
                    return result
                depth -= 1
            elif token.kind == "," and depth == 0:
                result.append(self.make_value(current))
                current = []
                continue
            current.append(token)

    def recover_cell_area(self, name, parent, values):
        """One explicit compatibility rule; never rewrite the frozen bytes."""
        if (self.profile != AREA_SEMICOLON_COMPAT_PROFILE or parent != "cell"
                or name.raw != "area" or len(values) != 1):
            return None
        number = values[0]
        following = self.tokens[self.i:self.i + 4]
        if (number.kind != "word" or len(number.raw) > 128 or number.line != name.line
                or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", number.raw)
                or not re.fullmatch(r"area[ \t]*:[ \t]*[0-9]+(?:\.[0-9]+)?",
                                    self.text[name.start:number.end])
                or len(following) != 4):
            return None
        next_name, colon, boolean, semicolon = following
        if (next_name.kind != "word" or next_name.raw != "is_macro_cell"
                or colon.kind != ":" or boolean.kind != "word"
                or boolean.raw not in {"true", "false"} or semicolon.kind != ";"
                or next_name.line != number.line + 1
                or any(token.line != next_name.line for token in following)
                or not re.fullmatch(r"[ \t]*(?:\r\n|\n|\r)[ \t]*",
                                    self.text[number.end:next_name.start])
                or not re.fullmatch(r"is_macro_cell[ \t]*:[ \t]*(?:true|false)[ \t]*;",
                                    self.text[next_name.start:semicolon.end])):
            return None
        diagnostic = {"kind": "missing_cell_area_semicolon_compatibility",
                      "profile": self.profile, "scope": "cell", "field": "area",
                      "line": name.line, "value_line": number.line, "raw_value": number.raw,
                      "next_field": "is_macro_cell", "next_field_line": next_name.line,
                      "source_fragment": self.text[name.start:next_name.start],
                      "recovery": "capture the numeric area as unterminated; retain original bytes and start the following statement at its original token"}
        self.diagnostics.append(diagnostic)
        return diagnostic

    def statement(self, depth=0, parent=None):
        if depth > 200:
            self.error("group nesting exceeds the profile limit", self.peek())
        name = self.pop()
        if name.kind != "word" or not _IDENT.fullmatch(name.value):
            self.error("expected a Liberty statement identifier", name)
        token = self.peek()
        if token is None:
            self.error("truncated Liberty statement", name)
        if token.kind == ":":
            self.pop()
            values, nesting = [], 0
            while True:
                if not nesting and self.recover_cell_area(name, parent, values) is not None:
                    last = values[-1]
                    return _Node("attribute", name.value, name.line, name.start, last.end,
                                 last.line, value=self.make_value(values),
                                 missing_semicolon_compatibility=True)
                token = self.pop()
                if token.kind == ";" and not nesting:
                    break
                if token.kind in {"{", "}"}:
                    self.error("attribute is missing its terminating semicolon", token)
                if token.kind == ":":
                    self.error("unexpected ':' in an attribute value; possible missing semicolon", token)
                if token.kind == "(":
                    nesting += 1
                elif token.kind == ")":
                    if not nesting:
                        self.error("unmatched parenthesis in attribute", token)
                    nesting -= 1
                values.append(token)
            return _Node("attribute", name.value, name.line, name.start, token.end,
                         token.line, value=self.make_value(values))
        args = self.arguments()
        token = self.pop()
        if token.kind == ";":
            return _Node("complex_attribute", name.value, name.line, name.start,
                         token.end, token.line, args=args)
        if token.kind != "{":
            self.error("expected ';' or '{' after argument list", token)
        children, attributes = [], set()
        while self.peek() is not None and self.peek().kind != "}":
            child = self.statement(depth + 1, parent=name.value)
            if child.kind == "attribute":
                if child.name in attributes:
                    self.error(f"duplicate attribute {child.name!r}",
                               _Token("", "", "", child.line, child.start, child.end), "duplicate")
                attributes.add(child.name)
            children.append(child)
        closing = self.expect("}")
        trailing = self.peek() is not None and self.peek().kind == ";"
        if trailing:
            closing = self.pop()
        return _Node("group", name.value, name.line, name.start, closing.end,
                     closing.line, args=args, children=children, trailing_semicolon=trailing)

    def parse(self):
        nodes = []
        while self.peek() is not None:
            nodes.append(self.statement())
        return nodes


class _Interface:
    def __init__(self, nodes, source_name):
        self.nodes, self.source_name = nodes, source_name
        self.diagnostics = []

    def error(self, message, node, code="invalid_interface"):
        raise LibertyProfileError(message, source_name=self.source_name,
                                  line=node.line, code=code)

    def name(self, node):
        if len(node.args) != 1 or node.args[0].scalar is None:
            self.error(f"{node.name} requires exactly one literal name", node)
        name = node.args[0].scalar
        if not name or len(name) > 2048 or any(char.isspace() for char in name):
            self.error("interface name is empty, too long, or contains whitespace", node)
        return name

    def attrs(self, node, allowed=None, complex_allowed=(), groups_allowed=()):
        attrs = {}
        for child in node.children:
            if child.kind == "group":
                if allowed is not None and child.name not in groups_allowed:
                    self.error(f"unsupported {node.name} interface group {child.name!r}", child,
                               "unsupported_interface")
                continue
            if allowed is not None and ((child.kind == "attribute" and child.name not in allowed)
                                        or (child.kind == "complex_attribute" and child.name not in complex_allowed)):
                self.error(f"unsupported {node.name} interface field {child.name!r}", child,
                           "unsupported_interface")
            if child.name in attrs:
                self.error(f"duplicate interface field {child.name!r}", child, "duplicate")
            attrs[child.name] = child
        return attrs

    def scalar(self, node, field_name, attrs, required=False):
        attribute = attrs.get(field_name)
        if attribute is None:
            if required:
                self.error(f"missing {field_name!r} in {node.name}", node)
            return None
        if attribute.kind != "attribute" or attribute.value.scalar is None:
            self.error(f"{field_name!r} requires one literal value", attribute)
        return attribute.value.scalar

    def fields(self, attrs):
        result = {}
        for name, node in attrs.items():
            if node.kind == "attribute":
                result[name] = {"raw": node.value.raw, "value": node.value.scalar,
                                "line": node.line, "value_line": node.value.line}
            else:
                result[name] = {"kind": "complex_attribute", "args": [arg.public() for arg in node.args],
                                "line": node.line}
        return result

    def integer(self, node, key, attrs):
        value = self.scalar(node, key, attrs, required=True)
        if len(value) > 8 or not _INTEGER.fullmatch(value):
            self.error(f"{key} must be a bounded nonnegative integer", attrs[key])
        result = int(value)
        if result > MAX_BITS:
            self.error(f"{key} exceeds profile bound {MAX_BITS}", attrs[key])
        return result

    def typedef(self, node):
        attrs = self.attrs(node, {"base_type", "data_type", "bit_width", "bit_from", "bit_to", "downto"})
        if self.scalar(node, "base_type", attrs, True) != "array" or self.scalar(node, "data_type", attrs, True) != "bit":
            self.error("only base_type=array/data_type=bit is supported for buses", node,
                       "unsupported_interface")
        width = self.integer(node, "bit_width", attrs)
        first, last = self.integer(node, "bit_from", attrs), self.integer(node, "bit_to", attrs)
        if width < 1 or width != abs(first - last) + 1:
            self.error("type bit_width does not match bit_from/bit_to", node)
        down = self.scalar(node, "downto", attrs)
        if down not in {None, "true", "false"}:
            self.error("downto must be true or false", attrs["downto"])
        if first != last and down is not None and ((down == "true") != (first > last)):
            self.error("downto contradicts bit_from/bit_to", node)
        step = -1 if first > last else 1
        return {"raw_name": self.name(node), "line": node.line,
                "bit_width": width, "bit_from": first, "bit_to": last,
                "indices": list(range(first, last + step, step)),
                "downto_declared": None if down is None else down == "true",
                "fields": self.fields(attrs)}

    def interface_fields(self, node, *, bus=False):
        allowed = _PIN_FIELDS | ({"bus_type"} if bus else set())
        attrs = self.attrs(node, allowed, _PIN_COMPLEX, _PIN_GROUPS | ({"pin"} if bus else set()))
        for key in _NUMERIC_FIELDS & attrs.keys():
            value = self.scalar(node, key, attrs, True)
            try:
                finite = len(value) <= 128 and _NUMBER.fullmatch(value) and Decimal(value).is_finite()
            except InvalidOperation:
                finite = False
            if not finite:
                self.error(f"{key} requires a finite numeric literal", attrs[key])
        expressions = {"function", "three_state", "power_down_function", "clamp_0_function", "clamp_1_function"}
        for key in attrs.keys() - expressions - _PIN_COMPLEX:
            self.scalar(node, key, attrs, True)
        direction = self.scalar(node, "direction", attrs)
        if direction is not None and direction not in _DIRECTIONS:
            self.error("unknown direction", attrs["direction"])
        clock = self.scalar(node, "clock", attrs)
        if clock not in {None, "true", "false"}:
            self.error("clock requires literal true/false", attrs["clock"])
        pg_type = self.scalar(node, "pg_type", attrs)
        if pg_type is not None and pg_type not in _PG_TYPES:
            self.error("unknown pg_type", attrs["pg_type"])
        return attrs, direction

    def pin(self, node, bus=None, bus_attrs=None):
        attrs, declared = self.interface_fields(node)
        raw_name = self.name(node)
        bus_direction = None if bus is None else bus["declared_direction"]
        overrides_bus = declared is not None and bus_direction is not None and declared != bus_direction
        if overrides_bus:
            self.diagnostics.append({"kind": "pin_direction_overrides_bus_default", "line": node.line,
                                     "raw_name": raw_name, "bus_raw_name": bus["raw_name"],
                                     "bus_direction": bus_direction, "pin_direction": declared})
        effective = declared if declared is not None else bus_direction
        if effective is None and node.name != "pg_pin":
            self.error("pin has no declared or inherited direction", node)
        if node.name == "pg_pin" and "pg_type" not in attrs:
            self.error("pg_pin requires explicit pg_type; no role inferred from name", node)
        direction_source = None
        if effective is not None:
            source_node = attrs["direction"] if declared is not None else bus_attrs["direction"]
            direction_source = {"scope": "pin" if declared is not None else "bus",
                                "raw_name": raw_name if declared is not None else bus["raw_name"],
                                "line": source_node.line}
        declaration = {"raw_name": raw_name, "name_spelling": node.args[0].raw,
                       "line": node.line, "kind": node.name,
                       "bus_raw_name": None if bus is None else bus["raw_name"],
                       "declared_direction": declared, "effective_direction": effective,
                       "direction_overrides_bus": overrides_bus,
                       "direction_source": direction_source, "fields": self.fields(attrs)}
        if bus is None:
            if re.search(r"\[[^\]]*:[^\]]*\]", raw_name):
                self.error("range pin outside a typed bus is ambiguous in this profile", node)
            names_indices = [(raw_name, None)]
            from_range = False
        else:
            match = _BIT_NAME.fullmatch(raw_name)
            if match is None or match[1] != bus["raw_name"]:
                self.error("bus child pin must use the exact bus[index] or bus[from:to] name", node)
            first = int(match[2])
            last = first if match[3] is None else int(match[3])
            if max(first, last) > MAX_BITS or abs(first - last) + 1 > MAX_BITS:
                self.error("pin range exceeds profile bound", node)
            step = -1 if first > last else 1
            indices = list(range(first, last + step, step))
            if not set(indices).issubset(set(bus["indices"])):
                self.error("pin range or index falls outside its bus type", node)
            names_indices = [(f"{bus['raw_name']}[{index}]", index) for index in indices]
            from_range = match[3] is not None
        declaration["bit_names"] = [name for name, _ in names_indices]
        expanded = []
        for bit_name, bit_index in names_indices:
            expanded.append({**declaration, "bit_name": bit_name, "bit_index": bit_index,
                             "name_origin": "range_expansion" if from_range else "literal",
                             "bus_fields": {} if bus is None else bus["fields"]})
        return declaration, expanded

    def check_placement(self, node, parent=None):
        if node.name in {"library", "cell", "type", "bus", "pin", "pg_pin", "bundle"} and node.kind != "group":
            self.error(f"{node.name} is an interface group, not an attribute", node)
        if node.kind != "group":
            return
        allowed_parent = {"library": None, "cell": "library", "type": "library",
                          "bus": "cell", "pg_pin": "cell"}
        if node.name == "bundle":
            self.error("bundle interface semantics are outside this profile", node, "unsupported_interface")
        if node.name in allowed_parent and parent != allowed_parent[node.name]:
            self.error(f"misplaced {node.name} interface group", node)
        if node.name == "pin" and parent not in {"cell", "bus"}:
            self.error("pin interface group is not directly under cell/bus", node)
        for child in node.children:
            self.check_placement(child, node.name)

    def extract(self):
        if len(self.nodes) != 1 or self.nodes[0].kind != "group" or self.nodes[0].name != "library":
            node = self.nodes[0] if self.nodes else _Node("", "", 1, 0, 0, 1)
            self.error("profile requires exactly one top-level library", node)
        library = self.nodes[0]
        self.check_placement(library)
        cells = [node for node in library.children if node.kind == "group" and node.name == "cell"]
        if len(cells) != 1:
            self.error("profile requires exactly one cell", library)
        # Library attributes and complex definitions remain in the AST. Only
        # units and bus naming affect this interface capture directly.
        library_attrs = {}
        for node in library.children:
            if node.kind != "group" and (node.name.endswith("_unit") or node.name == "bus_naming_style"):
                if node.name in library_attrs:
                    self.error(f"duplicate library field {node.name}", node)
                library_attrs[node.name] = node
        naming = self.scalar(library, "bus_naming_style", library_attrs)
        if naming not in {None, "%s[%d]"}:
            self.error("custom bus_naming_style is outside this explicit [] profile", library_attrs["bus_naming_style"],
                       "unsupported_interface")
        for key, node in library_attrs.items():
            if not key.endswith("_unit"):
                continue
            if node.kind == "attribute":
                self.scalar(library, key, library_attrs, True)
            elif key != "capacitive_load_unit" or len(node.args) != 2 or any(arg.scalar is None for arg in node.args):
                self.error("unsupported or ambiguous complex unit declaration", node)
        types = []
        type_map = {}
        for node in library.children:
            if node.kind == "group" and node.name == "type":
                typedef = self.typedef(node)
                if typedef["raw_name"] in type_map:
                    self.error("duplicate type name", node, "duplicate")
                type_map[typedef["raw_name"]] = typedef
                types.append(typedef)
        cell_node = cells[0]
        cell = {"raw_name": self.name(cell_node), "line": cell_node.line,
                "buses": [], "pins": [], "pg_pins": [], "bits": []}
        top_names, bit_names = set(), set()
        for node in cell_node.children:
            if node.kind == "group" and node.name not in _CELL_GROUPS:
                self.error(f"unsupported cell-level group {node.name!r}", node, "unsupported_interface")
            if node.kind != "group" or node.name not in {"bus", "pin", "pg_pin"}:
                continue
            name = self.name(node)
            if name in top_names:
                self.error("duplicate cell interface name", node, "duplicate")
            top_names.add(name)
            if node.name == "bus":
                attrs, direction = self.interface_fields(node, bus=True)
                type_name = self.scalar(node, "bus_type", attrs, True)
                if type_name not in type_map:
                    self.error("bus references unknown type", node)
                typedef = type_map[type_name]
                if any(char in name for char in "[]\\"):
                    self.error("bus stem with brackets/escapes is outside this profile", node,
                               "unsupported_interface")
                bus = {"raw_name": name, "line": node.line, "bus_type": type_name,
                       "indices": typedef["indices"][:], "bit_width": typedef["bit_width"],
                       "declared_direction": direction, "fields": self.fields(attrs), "pins": [],
                       "bit_names": [f"{name}[{index}]" for index in typedef["indices"]]}
                children = [child for child in node.children if child.kind == "group" and child.name == "pin"]
                local_bits, local_declarations = set(), set()
                for child in children:
                    declaration, bits = self.pin(child, bus, attrs)
                    if declaration["raw_name"] in local_declarations:
                        self.error("duplicate bus pin declaration", child, "duplicate")
                    local_declarations.add(declaration["raw_name"])
                    for bit in bits:
                        if bit["bit_name"] in local_bits:
                            self.error("overlapping/duplicate bus pin bit", child, "duplicate")
                        local_bits.add(bit["bit_name"])
                    bus["pins"].append(declaration)
                    cell["pins"].append(declaration)
                    self.add_bits(bits, cell, bit_names, child)
                if local_bits != set(bus["bit_names"]):
                    self.error("bus pin declarations do not cover every type bit exactly once", node)
                cell["buses"].append(bus)
            else:
                declaration, bits = self.pin(node)
                cell["pg_pins" if node.name == "pg_pin" else "pins"].append(declaration)
                self.add_bits(bits, cell, bit_names, node)
        if not cell["bits"]:
            self.error("interface profile requires at least one pin endpoint", cell_node)
        return {"library": {"raw_name": self.name(library), "line": library.line,
                            "units": self.fields({name: node for name, node in library_attrs.items() if name.endswith("_unit")}),
                            "bus_naming_style": None if "bus_naming_style" not in library_attrs else self.fields(library_attrs)["bus_naming_style"]},
                "types": types, "cell": cell,
                "ast": library.public(), "diagnostics": self.diagnostics,
                "qualification": "Interface syntax and explicit declarations only; no timing, PG connectivity, equivalence, routing, PPA or hard-macro qualification."}

    def add_bits(self, bits, cell, seen, node):
        for bit in bits:
            if bit["bit_name"] in seen:
                self.error("duplicate expanded cell bit name", node, "duplicate")
            seen.add(bit["bit_name"])
            cell["bits"].append(bit)


def parse_liberty(data: bytes, source_name: str = "", *, profile: str = PROFILE) -> dict:
    """Parse all syntax, then extract one complete, explicitly typed interface.

    ``cell.pins`` retains declarations; ``cell.bits`` contains expanded endpoints.
    Join by ``bit_name`` and ``effective_direction``, never declaration order.
    ``raw_name`` is the unchanged declaration name (possibly a range); quoted
    spelling is additionally retained in ``name_spelling``. Literal backslashes
    are not stripped. Only bus direction is inherited; other raw bus and pin
    fields are kept separately. Standalone scalar names are never guessed into
    buses, clocks or power pins.

    The default profile requires explicit semicolons. The separately selected
    ``AREA_SEMICOLON_COMPAT_PROFILE`` recognizes only a direct cell ``area``
    containing an unsigned plain decimal on one line, with the immediately
    following line exactly declaring ``is_macro_cell : true/false;``. It records
    the missing terminator without inserting bytes. Its output always has
    ``syntax_strict=False`` and does not assert that the input is valid Liberty.
    """
    if not isinstance(data, bytes):
        raise TypeError("parse_liberty expects bytes")
    if not isinstance(source_name, str):
        raise TypeError("source_name must be a string")
    if profile not in {PROFILE, AREA_SEMICOLON_COMPAT_PROFILE}:
        raise LibertyProfileError("unknown explicit parsing profile", source_name=source_name,
                                  code="unsupported_profile")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        raise LibertyProfileError("non-ASCII input", source_name=source_name,
                                  line=data[:error.start].count(b"\n") + 1,
                                  code="lexical_error") from error
    for line, contents in enumerate(text.splitlines(keepends=True), 1):
        if any((ord(char) < 32 and char not in "\t\r\n") or ord(char) == 127 for char in contents):
            raise LibertyProfileError("control character outside profile", source_name=source_name,
                                      line=line, code="lexical_error")
    syntax = _Syntax(text, source_name, profile)
    result = _Interface(syntax.parse(), source_name).extract()
    result["diagnostics"] = syntax.diagnostics + result["diagnostics"]
    if profile == AREA_SEMICOLON_COMPAT_PROFILE:
        result["qualification"] += " Selected syntax compatibility is not a valid-Liberty claim."
    return {"profile": profile, "source_name": source_name,
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "syntax_strict": profile == PROFILE,
            "syntax_recovery_count": len(syntax.diagnostics), **result}
