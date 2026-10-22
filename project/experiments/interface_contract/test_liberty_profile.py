"""Independent synthetic interface expectations and strict rejection cases."""

import hashlib
import json
import unittest

from liberty_profile import LibertyProfileError, PROFILE, parse_liberty


TYPE = """type (vec4) {
  base_type : array;
  data_type : bit;
  bit_width : 4;
  bit_from : 3;
  bit_to : 0;
  downto : true;
}
"""
BUS = """bus (DATA) {
  bus_type : vec4;
  direction : input;
  pin (DATA[3:0]) {
    capacitance : 0.01250;
  }
}
"""


def scalar(name="clk", fields="direction : input; clock : true;", groups=""):
    return f"pin ({name}) {{\n {fields}\n {groups}\n}}\n"


def library(contents=None, *, types=TYPE, metadata='time_unit : "1ns";\ncapacitive_load_unit (1, pf);',
            cell="macro", name="model"):
    if contents is None:
        contents = BUS + scalar()
    return (f"library ({name}) {{\n{metadata}\n{types}\ncell ({cell}) {{\n{contents}\n}}\n}}\n").encode("ascii")


def groups(node, name):
    return [child for child in node.get("children", []) if child["kind"] == "group" and child["name"] == name]


class LibertyProfileTests(unittest.TestCase):
    def reject(self, data, contains=None):
        with self.assertRaises(LibertyProfileError) as raised:
            parse_liberty(data, "synthetic.lib")
        error = raised.exception
        self.assertEqual(error.source_name, "synthetic.lib")
        self.assertGreaterEqual(error.line, 1)
        if contains:
            self.assertIn(contains, str(error))
        return error

    def test_complete_interface_schema_and_source_identity(self):
        data = library()
        parsed = parse_liberty(data, "synthetic.lib")
        self.assertEqual(parsed["profile"], PROFILE)
        self.assertEqual(parsed["source_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(parsed["library"]["raw_name"], "model")
        self.assertEqual(parsed["cell"]["raw_name"], "macro")
        self.assertEqual([bit["bit_name"] for bit in parsed["cell"]["bits"]],
                         ["DATA[3]", "DATA[2]", "DATA[1]", "DATA[0]", "clk"])
        self.assertEqual([bit["effective_direction"] for bit in parsed["cell"]["bits"]], ["input"] * 5)
        self.assertEqual(parsed["library"]["units"]["time_unit"]["raw"], '"1ns"')
        unit_args = parsed["library"]["units"]["capacitive_load_unit"]["args"]
        self.assertEqual([arg["value"] for arg in unit_args], ["1", "pf"])
        self.assertIn("no timing", parsed["qualification"])
        self.assertEqual(json.loads(json.dumps(parsed)), parsed)

    def test_range_name_and_expanded_bit_name_remain_distinct(self):
        parsed = parse_liberty(library())
        declaration = parsed["cell"]["pins"][0]
        self.assertEqual(declaration["raw_name"], "DATA[3:0]")
        self.assertEqual(declaration["name_spelling"], "DATA[3:0]")
        for index, bit in zip([3, 2, 1, 0], parsed["cell"]["bits"][:4]):
            self.assertEqual(bit["raw_name"], "DATA[3:0]")
            self.assertEqual(bit["bit_index"], index)
            self.assertEqual(bit["bit_name"], f"DATA[{index}]")
            self.assertEqual(bit["name_origin"], "range_expansion")

    def test_bus_direction_is_inherited_with_source_line(self):
        data = library(BUS)
        lines = data.decode().splitlines()
        parsed = parse_liberty(data)
        bit = parsed["cell"]["bits"][0]
        self.assertIsNone(bit["declared_direction"])
        self.assertEqual(bit["direction_source"], {"scope": "bus", "raw_name": "DATA",
                                                   "line": lines.index("  direction : input;") + 1})
        self.assertNotIn("direction", bit["fields"])
        self.assertEqual(bit["bus_fields"]["direction"]["value"], "input")

    def test_explicit_pin_direction_and_raw_electrical_fields(self):
        content = scalar("Y", 'direction : output; max_capacitance : 2.400e-2; capacitance : .001; clock : false; '
                         'related_power_pin : "VPWR"; related_ground_pin : "VGND";')
        parsed = parse_liberty(library(content))
        bit = parsed["cell"]["bits"][0]
        self.assertEqual(bit["declared_direction"], "output")
        self.assertEqual(bit["effective_direction"], "output")
        self.assertEqual(bit["direction_source"]["scope"], "pin")
        self.assertEqual(bit["fields"]["max_capacitance"]["raw"], "2.400e-2")
        self.assertEqual(bit["fields"]["capacitance"]["raw"], ".001")
        self.assertEqual(bit["fields"]["clock"]["value"], "false")
        self.assertEqual(bit["fields"]["related_power_pin"]["raw"], '"VPWR"')
        self.assertEqual(bit["fields"]["related_ground_pin"]["value"], "VGND")

    def test_non_direction_bus_fields_are_not_silently_inherited(self):
        content = BUS.replace("direction : input;", "direction : input; capacitance : 0.2; clock : false;")
        content = content.replace("    capacitance : 0.01250;", "")
        bit = parse_liberty(library(content))["cell"]["bits"][0]
        self.assertNotIn("capacitance", bit["fields"])
        self.assertNotIn("clock", bit["fields"])
        self.assertEqual(bit["bus_fields"]["capacitance"]["value"], "0.2")

    def test_individual_bus_bits_in_source_order_are_not_zipped_to_type_order(self):
        content = "bus(DATA) { bus_type:vec4; direction:output;\n"
        for index in [0, 2, 1, 3]:
            content += f"pin(DATA[{index}]) {{ max_capacitance:{index + 1}.0; }}\n"
        content += "}\n"
        parsed = parse_liberty(library(content))
        self.assertEqual([bit["bit_index"] for bit in parsed["cell"]["bits"]], [0, 2, 1, 3])
        by_name = {bit["bit_name"]: bit for bit in parsed["cell"]["bits"]}
        self.assertEqual(by_name["DATA[2]"]["fields"]["max_capacitance"]["value"], "3.0")
        self.assertEqual(parsed["cell"]["buses"][0]["bit_names"], ["DATA[3]", "DATA[2]", "DATA[1]", "DATA[0]"])

    def test_ascending_nonzero_type_range(self):
        typedef = TYPE.replace("bit_from : 3", "bit_from : 4").replace("bit_to : 0", "bit_to : 7").replace("downto : true", "downto : false")
        content = BUS.replace("DATA[3:0]", "DATA[4:7]")
        parsed = parse_liberty(library(content, types=typedef))
        self.assertEqual(parsed["types"][0]["indices"], [4, 5, 6, 7])
        self.assertEqual([bit["bit_name"] for bit in parsed["cell"]["bits"]], ["DATA[4]", "DATA[5]", "DATA[6]", "DATA[7]"])

    def test_single_bit_range_still_records_generated_name(self):
        typedef = TYPE.replace("bit_width : 4", "bit_width : 1").replace("bit_from : 3", "bit_from : 4").replace("bit_to : 0", "bit_to : 4")
        content = BUS.replace("DATA[3:0]", "DATA[4:4]")
        bit = parse_liberty(library(content, types=typedef))["cell"]["bits"][0]
        self.assertEqual((bit["raw_name"], bit["bit_name"], bit["name_origin"]),
                         ("DATA[4:4]", "DATA[4]", "range_expansion"))

    def test_standalone_bit_spelling_does_not_infer_a_typed_bus(self):
        bit = parse_liberty(library(scalar("flat[7]"), types=""))["cell"]["bits"][0]
        self.assertEqual(bit["bit_name"], "flat[7]")
        self.assertIsNone(bit["bus_raw_name"])
        self.assertIsNone(bit["bit_index"])
        self.assertEqual(bit["name_origin"], "literal")

    def test_comments_and_quoted_fake_pin_groups_cannot_create_endpoints(self):
        metadata = 'comment : "pin(fake) {direction:output;} // /* text */";\n' + \
                   '/* pin(also_fake){ direction:input; } */\n// pin(last_fake){}\n'
        parsed = parse_liberty(library(scalar("REAL"), metadata=metadata))
        self.assertEqual([bit["bit_name"] for bit in parsed["cell"]["bits"]], ["REAL"])
        comment = parsed["ast"]["children"][0]
        self.assertEqual(comment["name"], "comment")
        self.assertIn("pin(fake)", comment["value"]["value"])

    def test_timing_and_multiline_table_arguments_are_captured_generically(self):
        timing = ('timing () {\n related_pin : "DATA[0]";\n timing_type : setup_rising;\n'
                  ' rise_constraint (lut) {\n index_1 ("0.1, 0.2");\n'
                  ' values ( \\\n "1, 2", \\\n "3, 4" );\n }\n}\n')
        data = library(scalar("CLK", groups=timing))
        parsed = parse_liberty(data)
        cell = groups(parsed["ast"], "cell")[0]
        timing_node = groups(groups(cell, "pin")[0], "timing")[0]
        table = groups(timing_node, "rise_constraint")[0]
        values = next(node for node in table["children"] if node["name"] == "values")
        self.assertEqual(values["kind"], "complex_attribute")
        self.assertEqual([arg["value"] for arg in values["args"]], ["1, 2", "3, 4"])
        self.assertEqual([bit["bit_name"] for bit in parsed["cell"]["bits"]], ["CLK"])

    def test_quoted_escapes_and_continuations_keep_raw_values(self):
        metadata = 'comment : "escaped \\" quote and \\\\ path and pin(FAKE)";'
        data = library(scalar("X", 'direction:input; function:"a \\\n & b";'), metadata=metadata)
        parsed = parse_liberty(data)
        self.assertIn(r'\"', parsed["ast"]["children"][0]["value"]["value"])
        value = parsed["cell"]["bits"][0]["fields"]["function"]
        self.assertIn("\\\n", value["raw"])
        self.assertEqual(value["value"], "a  & b")

    def test_raw_quoted_and_escaped_names_are_retained_without_merging(self):
        content = scalar('"A[0]"') + scalar(r"A\[0\]") + scalar(r"unit\/B")
        parsed = parse_liberty(library(content))
        self.assertEqual([bit["bit_name"] for bit in parsed["cell"]["bits"]], ["A[0]", r"A\[0\]", r"unit\/B"])
        self.assertEqual(parsed["cell"]["pins"][0]["name_spelling"], '"A[0]"')
        self.assertEqual(parsed["cell"]["pins"][1]["raw_name"], r"A\[0\]")

    def test_original_lines_for_pin_and_fields(self):
        data = b"// preface\n\n" + library(scalar("X", "direction:input;\n capacitance:0.125;"))
        lines = data.decode().splitlines()
        bit = parse_liberty(data)["cell"]["bits"][0]
        self.assertEqual(bit["line"], lines.index("pin (X) {") + 1)
        self.assertEqual(bit["fields"]["capacitance"]["line"], lines.index(" capacitance:0.125;") + 1)
        bad = data.replace(b"capacitance:0.125", b"capacitance:NaN")
        error = self.reject(bad)
        self.assertEqual(error.line, bit["fields"]["capacitance"]["line"])

    def test_pg_metadata_is_explicit_and_no_role_is_guessed_from_vdd_name(self):
        content = scalar("VDD", "direction:inout;") + ('pg_pin(VSS) { pg_type:primary_ground; voltage_name:"VSS"; }\n')
        parsed = parse_liberty(library(content))
        ordinary, pg = parsed["cell"]["bits"]
        self.assertEqual(ordinary["kind"], "pin")
        self.assertNotIn("pg_type", ordinary["fields"])
        self.assertEqual(pg["kind"], "pg_pin")
        self.assertIsNone(pg["effective_direction"])
        self.assertEqual(pg["fields"]["pg_type"]["value"], "primary_ground")
        self.assertEqual(pg["fields"]["voltage_name"]["raw"], '"VSS"')

    def test_duplicate_cell_pins_pg_names_and_bus_bits_are_rejected(self):
        variants = [scalar("X") + scalar("X"),
                    scalar("VDD", "direction:inout;") + "pg_pin(VDD){pg_type:primary_power;}",
                    "bus(DATA){bus_type:vec4;direction:input;pin(DATA[3:1]){}pin(DATA[1:0]){}}",
                    BUS + scalar("DATA[0]"), BUS + BUS]
        for content in variants:
            with self.subTest(content=content):
                self.reject(library(content), "duplicate")

    def test_missing_bus_bits_are_not_silently_fabricated(self):
        for pins in ["", "pin(DATA[3:1]){}", "pin(DATA[0]){} pin(DATA[1]){} pin(DATA[2]){}"]:
            with self.subTest(pins=pins):
                content = "bus(DATA){bus_type:vec4;direction:input;" + pins + "}"
                self.reject(library(content), "cover every type bit")

    def test_wrong_bus_stem_out_of_range_and_ambiguous_ranges_are_rejected(self):
        for name in ["OTHER[3:0]", "DATA[4:0]", "DATA[3:-1]", "DATA[x]", "DATA[01]", "DATA", "DATA[1][0]"]:
            with self.subTest(name=name):
                self.reject(library(BUS.replace("DATA[3:0]", name)))
        self.reject(library(scalar("DATA[3:0]")), "outside a typed bus")

    def test_type_range_width_direction_and_missing_fields_are_rejected(self):
        bad_types = [TYPE.replace("bit_width : 4", "bit_width : 3"),
                     TYPE.replace("bit_width : 4", "bit_width : 0"),
                     TYPE.replace("bit_from : 3", "bit_from : -1"),
                     TYPE.replace("bit_to : 0", "bit_to : 0.0"),
                     TYPE.replace("downto : true", "downto : false"),
                     TYPE.replace("downto : true", "downto : yes"),
                     TYPE.replace("  bit_width : 4;\n", ""),
                     TYPE.replace("data_type : bit", "data_type : integer"),
                     TYPE.replace("bit_width : 4", "bit_width : 999999999999999999999"),
                     TYPE.replace("bit_to : 0", "bit_to : 65537")]
        for typedef in bad_types:
            with self.subTest(typedef=typedef):
                self.reject(library(types=typedef))

    def test_unknown_bus_type_and_duplicate_type_name_are_rejected(self):
        self.reject(library(BUS.replace("vec4", "unknown")), "unknown type")
        self.reject(library(types=TYPE + TYPE), "duplicate type")

    def test_missing_or_unknown_direction_is_rejected(self):
        self.reject(library(scalar("X", "capacitance:0.1;")), "no declared or inherited direction")
        self.reject(library(scalar("X", "direction:sideways;")), "unknown direction")
        content = BUS.replace("capacitance : 0.01250;", "direction:input;")
        bit = parse_liberty(library(content))["cell"]["bits"][0]
        self.assertEqual(bit["direction_source"]["scope"], "pin")

    def test_explicit_pin_direction_overrides_bus_default(self):
        parsed = parse_liberty(library(BUS.replace("capacitance : 0.01250;", "direction:output;")))
        for bit in parsed["cell"]["bits"]:
            self.assertEqual(bit["effective_direction"], "output")
            self.assertEqual(bit["declared_direction"], "output")
            self.assertEqual(bit["bus_fields"]["direction"]["value"], "input")
            self.assertTrue(bit["direction_overrides_bus"])
            self.assertEqual(bit["direction_source"]["scope"], "pin")
        self.assertEqual(parsed["diagnostics"][0]["kind"], "pin_direction_overrides_bus_default")

    def test_unknown_interface_field_group_or_bus_style_is_rejected(self):
        variants = [library(scalar("X", "direction:input; mystery_pin_semantics:true;")),
                    library(BUS.replace("bus_type : vec4;", "bus_type : vec4; mysterious_map:1;")),
                    library(scalar("X", groups="mystery_access(){}")),
                    library(scalar() + "mystery_port(X){}"),
                    library(scalar() + "bundle(B){members(A,B);}"),
                    library(types=TYPE.replace("data_type : bit;", "data_type : bit; unknown_type_rule:1;")),
                    library(metadata='bus_naming_style:"%s<%d>";')]
        for data in variants:
            with self.subTest(data=data):
                self.reject(data)

    def test_duplicate_attributes_and_complex_interface_values_are_rejected(self):
        self.reject(library(scalar("X", "direction:input;direction:output;")), "duplicate")
        self.reject(library(scalar("X", "direction(input);")))
        self.reject(library(scalar("X", "direction:input;clock:true;clock:false;")), "duplicate")
        self.reject(library(scalar("X", "direction:input;related_power_pin:VDD VCC;")), "one literal")

    def test_nonfinite_or_ambiguous_electrical_values_are_rejected(self):
        for value in ["NaN", "Inf", "-Infinity", "1_0", "one", "0.1 + 0.2", "1e99999999999999999999999999999"]:
            with self.subTest(value=value):
                self.reject(library(scalar("X", f"direction:input;capacitance:{value};")))
        self.reject(library(scalar("X", "direction:input;clock:1;")))
        self.reject(library("pg_pin(VDD){voltage_name:VDD;}"), "requires explicit pg_type")
        self.reject(library("pg_pin(VDD){pg_type:made_up_power;}"), "unknown pg_type")

    def test_misplaced_pin_cell_type_and_bus_groups_are_rejected(self):
        variants = [library(scalar("X", groups="timing(){pin(HIDDEN){direction:input;}}")),
                    library(scalar() + "type(other){}"),
                    library(scalar() + "timing(){bus(HIDDEN){}}"),
                    library(scalar(), metadata="pin(HIDDEN){direction:input;}"),
                    library(scalar() + "cell(nested){}")]
        for data in variants:
            with self.subTest(data=data):
                self.reject(data, "misplaced" if b"pin(HIDDEN)" not in data else None)

    def test_interface_keywords_cannot_hide_as_attributes(self):
        for data in [library(scalar() + "pin(HIDDEN);"),
                     library(scalar(), metadata="pin:hidden;"),
                     library(scalar(), metadata="type(ghost);"),
                     library(scalar() + "bus:unexpanded;")]:
            with self.subTest(data=data):
                self.reject(data, "interface group, not an attribute")

    def test_multiple_library_cell_and_trailing_statements_are_rejected(self):
        self.reject(library() + library(), "one top-level library")
        data = library().replace(b"cell (macro) {", b"cell(extra){pin(Z){direction:input;}}\ncell (macro) {")
        self.reject(data, "one cell")
        self.reject(library() + b"area:1;", "one top-level library")
        self.reject(b"library(model){}", "one cell")
        self.reject(library("", types=""), "at least one pin")

    def test_truncation_bad_braces_parentheses_and_missing_semicolons_are_rejected(self):
        data = library()
        variants = [data[:-3], data[:data.index(b"capacitance") + 5],
                    data.replace(b"direction : input;", b"direction : input"),
                    data.replace(b"bit_width : 4;", b"bit_width : 4"),
                    data.replace(b'time_unit : "1ns";', b'time_unit : "1ns"'),
                    data.replace(b"pin (DATA[3:0])", b"pin (DATA[3:0]"),
                    data.replace(b"capacitive_load_unit (1, pf)", b"capacitive_load_unit (1,,pf)"),
                    data + b"}"]
        for malformed in variants:
            with self.subTest(data=malformed):
                self.reject(malformed)

    def test_broken_comments_strings_controls_and_non_ascii_are_rejected(self):
        variants = [library() + b"/* unfinished", library() + b'"unfinished',
                    library() + b"/* a /* nested */ b */", library() + b"// \x00\n",
                    library().replace(b"macro", b"ma\xffcro"),
                    library().replace(b"clk", b"cl\x7fk"),
                    library().replace(b"clk", b"clk\\ ")]
        for malformed in variants:
            with self.subTest(data=malformed):
                self.reject(malformed)
        with self.assertRaises(TypeError):
            parse_liberty("not bytes")
        with self.assertRaises(TypeError):
            parse_liberty(library(), source_name=1)

    def test_crlf_and_bare_identifier_continuation(self):
        data = library(scalar("X", "direc\\\ntion:input;")).replace(b"\n", b"\r\n")
        bit = parse_liberty(data)["cell"]["bits"][0]
        self.assertEqual(bit["effective_direction"], "input")
        self.assertEqual(bit["fields"]["direction"]["line"], bit["line"] + 1)

    def test_generic_complex_definitions_and_nested_expressions_are_not_lost(self):
        metadata = ('define(custom1, pin, string);\ndefine(custom2, cell, integer);\n'
                    'lu_table_template(lut) { variable_1:input_net_transition; index_1("1, 2"); }\n')
        parsed = parse_liberty(library(scalar("X", 'direction:input;function:(A & (B | C));'), metadata=metadata))
        self.assertEqual(len([node for node in parsed["ast"]["children"] if node["name"] == "define"]), 2)
        function = parsed["cell"]["bits"][0]["fields"]["function"]
        self.assertEqual(function["raw"], "(A & (B | C))")
        self.assertIsNone(function["value"])


if __name__ == "__main__":
    unittest.main()
