"""Synthetic semantic/negative tests; no actual macro source is needed."""

import hashlib
import json
import unittest

from lef_profile import LEFProfileError, PROFILE, parse_lef


HEADER = ('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n'
          'UNITS\n  DATABASE MICRONS 2000 ;\nEND UNITS\n')


def pin(name="A[0]", *, direction="INPUT", use="SIGNAL", rects="RECT 0 0 1 1 ;"):
    return (f"PIN {name}\n  DIRECTION {direction} ;\n  USE {use} ;\n"
            f"  PORT\n    LAYER metal7 ;\n    {rects}\n  END\nEND {name}\n")


def lef(body=None, *, declarations="", size="SIZE 4 BY 3 ;", header=HEADER,
        name="M", end_library=True):
    body = pin() if body is None else body
    return (header + f"MACRO {name}\n  CLASS BLOCK ;\n  {size}\n" + declarations
            + body + f"END {name}\n" + ("END LIBRARY\n" if end_library else "")).encode("ascii")


class LEFProfileTests(unittest.TestCase):
    def reject(self, data, *, contains=None):
        with self.assertRaises(LEFProfileError) as raised:
            parse_lef(data, "synthetic.lef")
        self.assertGreaterEqual(raised.exception.line, 1)
        self.assertEqual(raised.exception.source_name, "synthetic.lef")
        if contains:
            self.assertIn(contains, str(raised.exception))
        return raised.exception

    def test_minimal_capture_is_json_serializable_and_exact(self):
        data = lef(pin(rects="RECT 0.0005 0.001 +1.2500 2e0 ;"))
        captured = parse_lef(data, "synthetic.lef")
        self.assertEqual(captured["profile"], PROFILE)
        self.assertEqual(captured["source_name"], "synthetic.lef")
        self.assertEqual(captured["source_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(captured["header"], {"version": "5.8", "dbu_per_micron": 2000,
                                             "busbitchars": "[]", "dividerchar": "/"})
        macro = captured["macro"]
        self.assertEqual(macro["size_um"], ["4", "3"])
        self.assertEqual(macro["size_dbu"], [8000, 6000])
        rect = macro["pins"][0]["ports"][0]["rects"][0]
        self.assertEqual(rect["rect_um"], ["0.0005", "0.001", "+1.2500", "2e0"])
        self.assertEqual(rect["rect_dbu"], [1, 2, 2500, 4000])
        self.assertEqual(captured["diagnostics"], [])
        self.assertEqual(json.loads(json.dumps(captured)), captured)

    def test_multiple_ports_layers_rectangles_and_pg_are_not_merged(self):
        body = ("PIN VDD\n DIRECTION INOUT ;\n USE POWER ;\n"
                " PORT\n  CLASS CORE ;\n  LAYER metal7 ;\n"
                "  RECT 0 0 1 1 ;\n  RECT 2 0 3 1 ;\n"
                "  LAYER metal8 ;\n  RECT 0 0 1 1 ;\n END\n"
                " PORT\n  LAYER metal7 ;\n  RECT 0 0 1 1 ;\n END\nEND VDD\n"
                + pin("VSS", direction="INOUT", use="GROUND"))
        captured = parse_lef(lef(body))
        power, ground = captured["macro"]["pins"]
        self.assertEqual((power["direction"], power["use"]), ("INOUT", "POWER"))
        self.assertEqual(ground["use"], "GROUND")
        self.assertEqual([port["index"] for port in power["ports"]], [0, 1])
        self.assertEqual([len(port["rects"]) for port in power["ports"]], [3, 1])
        self.assertEqual([rect["layer"] for rect in power["ports"][0]["rects"]],
                         ["metal7", "metal7", "metal8"])
        self.assertEqual(power["ports"][0]["class"], "CORE")
        self.assertEqual(captured["diagnostics"], [])

    def test_bare_bus_and_escaped_literal_names_stay_distinct(self):
        names = ["A[0]", r"A\[0\]", "tile/A", r"tile\/A", r"A\;B", "A#B"]
        captured = parse_lef(lef("".join(pin(name) for name in names)))
        self.assertEqual([item["name"] for item in captured["macro"]["pins"]], names)
        self.assertEqual(len(set(item["name"] for item in captured["macro"]["pins"])), 6)

    def test_origin_and_symmetry_omission_remain_explicit(self):
        macro = parse_lef(lef())["macro"]
        self.assertIsNone(macro["origin_um"])
        self.assertIsNone(macro["origin_dbu"])
        self.assertFalse(macro["origin_explicit"])
        self.assertIsNone(macro["symmetry"])
        self.assertEqual(macro["bbox_check"], "raw_size_box")

    def test_nonzero_origin_and_foreign_do_not_transform_coordinates(self):
        declarations = " ORIGIN 3 4 ;\n SYMMETRY X Y R90 ;\n FOREIGN other 7 8 FN ;\n"
        captured = parse_lef(lef(pin(rects="RECT -3 -4 -2 -3 ;"), declarations=declarations))
        macro = captured["macro"]
        self.assertTrue(macro["origin_explicit"])
        self.assertEqual(macro["origin_um"], ["3", "4"])
        self.assertEqual(macro["origin_dbu"], [6000, 8000])
        self.assertEqual(macro["symmetry"], ["X", "Y", "R90"])
        self.assertEqual(macro["pins"][0]["ports"][0]["rects"][0]["rect_dbu"],
                         [-6000, -8000, -4000, -6000])
        self.assertEqual(macro["foreign"][0]["orientation"], "FN")
        self.assertEqual(macro["bbox_check"], "not_evaluated_nonzero_origin")
        self.assertEqual([item["kind"] for item in captured["diagnostics"]],
                         ["bbox_check_not_evaluated"])

    def test_foreign_declarations_preserve_optional_fields(self):
        captured = parse_lef(lef(declarations="FOREIGN M ;\nFOREIGN alternate 0 1 ;\n"))
        first, second = captured["macro"]["foreign"]
        self.assertEqual(first["tokens"], ["M"])
        self.assertIsNone(first["point_um"])
        self.assertIsNone(first["orientation"])
        self.assertEqual(second["tokens"], ["alternate", "0", "1"])
        self.assertEqual(second["point_dbu"], [0, 2000])
        self.assertIsNone(second["orientation"])

    def test_outside_pg_geometry_is_retained_and_diagnosed(self):
        data = lef(pin("VDD", direction="INOUT", use="POWER", rects="RECT -1 0 5 1 ;"),
                   declarations="ORIGIN -0.0 +0 ;\n")
        captured = parse_lef(data)
        rect = captured["macro"]["pins"][0]["ports"][0]["rects"][0]
        self.assertEqual(rect["rect_dbu"], [-2000, 0, 10000, 2000])
        outside = captured["diagnostics"][0]
        self.assertEqual((outside["kind"], outside["pin"], outside["port_index"]),
                         ("outside_macro_size", "VDD", 0))
        self.assertEqual(captured["macro"]["bbox_check"], "raw_size_box")
        self.assertEqual(parse_lef(lef(pin(rects="RECT 0 0 4 3 ;")))["diagnostics"], [])

    def test_obstructions_and_duplicate_rectangles_preserve_evidence(self):
        body = pin() + ("OBS\n LAYER metal1 ;\n RECT 0 0 4 3 ;\n"
                        " RECT 0.0 0.0 4.0 3.0 ;\n LAYER metal10 ;\n"
                        " RECT 0 0 4 3 ;\nEND\n")
        captured = parse_lef(lef(body))
        obstruction = captured["macro"]["obstructions"][0]
        self.assertEqual(obstruction["index"], 0)
        self.assertEqual(len(obstruction["rects"]), 3)
        self.assertEqual(len(obstruction["layer_declarations"]), 2)
        duplicate = captured["diagnostics"][0]
        self.assertEqual((duplicate["kind"], duplicate["scope"], duplicate["obs_index"]),
                         ("duplicate_rect", "obstruction", 0))
        self.assertLess(duplicate["first_line"], duplicate["line"])
        self.assertEqual(len(captured["diagnostics"]), 1)

    def test_lines_and_error_context_refer_to_original_input(self):
        data = b"# leading comment\n\n" + lef()
        lines = data.decode("ascii").splitlines()
        captured = parse_lef(data, "original.lef")
        macro = captured["macro"]
        self.assertEqual(macro["line"], lines.index("MACRO M") + 1)
        source_pin = macro["pins"][0]
        self.assertEqual(source_pin["line"], lines.index("PIN A[0]") + 1)
        self.assertEqual(source_pin["ports"][0]["line"], lines.index("  PORT") + 1)
        rect = source_pin["ports"][0]["rects"][0]
        self.assertEqual(rect["line"], lines.index("    RECT 0 0 1 1 ;") + 1)
        error = self.reject(data.replace(b"RECT 0 0 1 1 ;", b"POLYGON 0 0 1 1 ;"))
        self.assertEqual(error.line, rect["line"])
        self.assertEqual(error.code, "unsupported_syntax")

    def test_half_dbu_is_rejected_without_rounding(self):
        error = self.reject(lef(pin(rects="RECT 0.00025 0 1 1 ;")))
        self.assertEqual(error.code, "fractional_dbu")
        self.reject(lef(declarations="ORIGIN 0.00025 0 ;\n"), contains="integer DBU")
        self.reject(lef(size="SIZE 4.00025 BY 3 ;"), contains="integer DBU")

    def test_nonfinite_malformed_and_extreme_coordinates_are_rejected(self):
        for value in ["NaN", "Inf", "+Inf", "-Infinity", "1_0", ".", "1e101", "1e-101"]:
            with self.subTest(value=value):
                self.reject(lef(pin(rects=f"RECT {value} 0 1 1 ;")))

    def test_zero_area_reversed_rectangles_and_invalid_sizes_are_rejected(self):
        for rect in ["0 0 0 1", "0 1 1 1", "2 0 1 1", "0 2 1 1"]:
            with self.subTest(rect=rect):
                self.reject(lef(pin(rects=f"RECT {rect} ;")), contains="positive area")
        for size in ["SIZE 0 BY 3 ;", "SIZE -1 BY 3 ;", "SIZE 4 3 ;", ""]:
            with self.subTest(size=size):
                self.reject(lef(size=size))

    def test_unsupported_geometry_cannot_be_silently_skipped(self):
        for shape in ["POLYGON 0 0 1 0 1 1 ;", "PATH 0 0 1 1 ;", "VIA 0 0 V12 ;",
                      "MASK 1 ;", "RECT MASK 1 0 0 1 1 ;",
                      "RECT 0 0 1 1 ITERATE DO 2 BY 2 STEP 1 1 ;"]:
            with self.subTest(shape=shape):
                self.reject(lef(pin(rects=shape)))
        self.reject(lef().replace(b"LAYER metal7 ;", b"LAYER metal7 MASK 1 ;"))
        self.reject(lef(pin() + "OBS\n LAYER metal1 ;\n POLYGON 0 0 1 1 ;\nEND\n"))

    def test_unknown_metadata_at_every_scope_is_rejected(self):
        variants = [HEADER.replace("UNITS\n", "NAMESCASESENSITIVE ON ;\nUNITS\n") + "MACRO M\n",
                    lef(declarations='PROPERTY custom "x" ;\n').decode("ascii"),
                    lef().decode("ascii").replace("  DIRECTION INPUT ;", "  NETEXPR a ;"),
                    lef().decode("ascii").replace("    RECT 0 0 1 1 ;", "    WIDTH 0.5 ;"),
                    lef().decode("ascii").replace("DATABASE MICRONS 2000 ;",
                                                   "DATABASE MICRONS 2000 ;\n CAPACITANCE PICOFARADS 1 ;")]
        for text in variants:
            with self.subTest(text=text):
                self.reject(text.encode("ascii"))

    def test_duplicate_declarations_and_pin_names_are_rejected(self):
        variants = [lef(pin() + pin()), lef(declarations="ORIGIN 0 0 ;\nORIGIN 0 0 ;\n"),
                    lef(declarations="CLASS BLOCK ;\n"),
                    lef(declarations="FOREIGN M ;\nFOREIGN M ;\n"),
                    lef().replace(b"USE SIGNAL ;", b"USE SIGNAL ;\n USE POWER ;"),
                    lef().replace(b"DIRECTION INPUT ;", b"DIRECTION INPUT ;\n DIRECTION OUTPUT ;"),
                    lef(header=HEADER + "VERSION 5.8 ;\n")]
        for data in variants:
            with self.subTest(data=data):
                self.reject(data, contains="duplicate")

    def test_missing_semicolons_and_mismatched_end_names_are_rejected(self):
        data = lef()
        for before, after in [(b"VERSION 5.8 ;", b"VERSION 5.8"),
                              (b"SIZE 4 BY 3 ;", b"SIZE 4 BY 3"),
                              (b"LAYER metal7 ;", b"LAYER metal7"),
                              (b"RECT 0 0 1 1 ;", b"RECT 0 0 1 1"),
                              (b"END A[0]", b"END A[1]"),
                              (b"END M\n", b"END OTHER\n"),
                              (b"END UNITS", b"END UNIT")]:
            with self.subTest(before=before):
                self.reject(data.replace(before, after))

    def test_truncated_scopes_and_extra_trailing_input_are_rejected(self):
        data = lef()
        for marker in [b"DATABASE MICRONS", b"MACRO", b"DIRECTION", b"RECT 0", b"END A[0]", b"END M"]:
            with self.subTest(marker=marker):
                self.reject(data[:data.index(marker) + len(marker) - 1])
        self.reject(data + b"PROPERTY late 1 ;\n")
        self.reject(lef(end_library=False) + b"MACRO SECOND\n SIZE 1 BY 1 ;\nEND SECOND\n")
        self.assertFalse(parse_lef(lef(end_library=False))["end_library_explicit"])

    def test_empty_port_missing_layer_and_empty_layer_are_rejected(self):
        bodies = ["PIN A\n DIRECTION INPUT ;\n USE SIGNAL ;\nEND A\n",
                  "PIN A\n PORT\nEND\nEND A\n",
                  "PIN A\n PORT\n RECT 0 0 1 1 ;\nEND\nEND A\n",
                  "PIN A\n PORT\n LAYER metal1 ;\nEND\nEND A\n",
                  "PIN A\n PORT\n LAYER metal1 ;\n LAYER metal2 ;\n RECT 0 0 1 1 ;\nEND\nEND A\n",
                  pin() + "OBS\nEND\n"]
        for body in bodies:
            with self.subTest(body=body):
                self.reject(lef(body))

    def test_units_and_version_are_explicit_profile_requirements(self):
        for factor in ["0", "-2000", "2000.0", "3", "9" * 5000]:
            with self.subTest(factor=factor[:20]):
                self.reject(lef(header=HEADER.replace("MICRONS 2000", "MICRONS " + factor)))
        self.reject(lef(header=HEADER.replace("VERSION 5.8 ;\n", "")))
        self.reject(lef(header=HEADER.replace("5.8", "5.7")))
        self.reject(lef(header='VERSION 5.8 ;\n'))
        captured = parse_lef(lef(header=HEADER.replace("MICRONS 2000", "MICRONS 1000")))
        self.assertEqual(captured["macro"]["size_dbu"], [4000, 3000])

    def test_optional_metadata_is_not_invented(self):
        data = lef().replace(b'BUSBITCHARS "[]" ;\n', b"").replace(b'DIVIDERCHAR "/" ;\n', b"")
        data = data.replace(b"  CLASS BLOCK ;\n", b"").replace(b"  DIRECTION INPUT ;\n", b"")
        data = data.replace(b"  USE SIGNAL ;\n", b"")
        captured = parse_lef(data)
        self.assertIsNone(captured["header"]["busbitchars"])
        self.assertIsNone(captured["header"]["dividerchar"])
        self.assertIsNone(captured["macro"]["class"])
        self.assertEqual([item["kind"] for item in captured["diagnostics"]],
                         ["missing_pin_direction", "missing_pin_use"])

    def test_comments_custom_delimiters_and_crlf(self):
        header = HEADER.replace('"[]"', '"<>"').replace('"/"', '"|"')
        data = lef(pin("A<0>"), header=header).replace(b"CLASS BLOCK ;", b"CLASS BLOCK ; # ignored text")
        captured = parse_lef(data.replace(b"\n", b"\r\n"))
        self.assertEqual(captured["header"]["busbitchars"], "<>")
        self.assertEqual(captured["header"]["dividerchar"], "|")
        self.assertEqual(captured["macro"]["pins"][0]["name"], "A<0>")

    def test_invalid_attributes_and_quoted_identifiers_are_rejected(self):
        for before, after in [(b"INPUT ;", b"SIDEWAYS ;"), (b"SIGNAL ;", b"DATA ;"),
                              (b"CLASS BLOCK ;", b"CLASS UNKNOWN ;"),
                              (b"PIN A[0]", b'PIN "A[0]"')]:
            with self.subTest(after=after):
                self.reject(lef().replace(before, after))
        self.reject(lef(declarations="SYMMETRY X X ;\n"))
        self.reject(lef(declarations="FOREIGN M 0 0 R90 ;\n"))
        captured = parse_lef(lef(pin(direction="OUTPUT TRISTATE")))
        output = captured["macro"]["pins"][0]
        self.assertEqual(output["direction"], "OUTPUT")
        self.assertTrue(output["output_tristate"])

    def test_non_ascii_controls_and_broken_lexical_tokens_are_rejected(self):
        for data in [lef() + b"# \xff\n", lef() + b"# \x00\n", lef().replace(b"metal7", b"metal\x007"),
                     lef().replace(b'"[]"', b'"[\n]"'),
                     lef().replace(b'"[]"', b'"[]'),
                     lef().replace(b"PIN A[0]", b"PIN A\\\n"),
                     lef().replace(b'"[]"', b'"[]"garbage')]:
            with self.subTest(data=data):
                self.reject(data)
        with self.assertRaises(TypeError):
            parse_lef("not bytes")
        with self.assertRaises(TypeError):
            parse_lef(lef(), source_name=1)


if __name__ == "__main__":
    unittest.main()
