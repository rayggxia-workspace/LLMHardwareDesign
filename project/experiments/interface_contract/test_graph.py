"""Focused invariant and refusal tests for the recorded ACT/MXU graph."""
from copy import deepcopy
import unittest

from graph import GraphError, build_graph


EXTERNAL = (
    ("clk", "input", 1, "both"),
    ("we", "input", 4, "ACT20"), ("w_row", "input", 8, "ACT20"),
    ("w_idx", "input", 32, "ACT20"), ("w_data", "input", 32, "ACT20"),
    ("w_dup", "input", 1, "ACT20"), ("w_off", "input", 8, "ACT20"),
    ("swe", "input", 1, "ACT20"), ("s_row", "input", 8, "ACT20"),
    ("s_blk", "input", 16, "ACT20"), ("s_data", "input", 64, "ACT20"),
    ("rst", "input", 1, "MXU20"), ("start", "input", 1, "MXU20"),
    ("go", "input", 1, "MXU20"), ("cmd", "input", 240, "MXU20"),
    ("rdy", "output", 1, "MXU20"), ("done", "output", 1, "MXU20"),
    ("computing", "output", 1, "MXU20"), ("pf_level", "output", 7, "MXU20"),
    ("pf_starve", "output", 1, "MXU20"), ("pf_block", "output", 1, "MXU20"),
    ("pf_u", "output", 1, "MXU20"), ("pf_uv", "output", 128, "MXU20"),
    ("a_req", "output", 1, "MXU20"), ("a_addr", "output", 32, "MXU20"),
    ("a_gnt", "input", 1, "MXU20"), ("a_rvalid", "input", 1, "MXU20"),
    ("a_rdata", "input", 256, "MXU20"), ("b_req", "output", 1, "MXU20"),
    ("b_addr", "output", 32, "MXU20"), ("b_gnt", "input", 1, "MXU20"),
    ("b_rvalid", "input", 1, "MXU20"), ("b_rdata", "input", 256, "MXU20"),
    ("t_ren", "output", 4, "MXU20"), ("t_raddr", "output", 128, "MXU20"),
    ("t_rdata", "input", 128, "MXU20"), ("t_wen", "output", 4, "MXU20"),
    ("t_waddr", "output", 128, "MXU20"), ("t_wdata", "output", 128, "MXU20"),
    ("t_gnt", "input", 1, "MXU20"),
)
LINKS = (
    ("ren", "act_ren", 2, "MXU20"), ("r_use", "computing", 1, "MXU20"),
    ("r_blk", "act_blk", 16, "MXU20"), ("r_blk2", "act_blk2", 16, "MXU20"),
    ("r_hi", "act_hi", 2, "MXU20"), ("r_grp", "act_grp", 8, "MXU20"),
    ("r_data", "act_data", 512, "ACT20"), ("r_scale", "act_scale", 128, "ACT20"),
)


def fixture():
    contract = dict(top="llhd_opentpu_hierarchy_preparation", external_signal_bits=1662,
                    external_ports={n: dict(direction=d, width=w) for n, d, w, _ in EXTERNAL},
                    connections=[dict(act_port=a, mxu_port=m, width=w, exact_bit_identity=True)
                                 for a, m, w, _ in LINKS],
                    address_and_data_bits=684, computing_feedback_bits=1,
                    shared_clock="clk", added_registers=0)
    views = {c: dict(ports={}, bits={}) for c in ("ACT20", "MXU20")}

    def port(candidate, name, direction, width):
        names = [name] if width == 1 else [f"{name}[{i}]" for i in range(width)]
        views[candidate]["ports"][name] = dict(direction=direction, width=width, bits=names)
        views[candidate]["bits"].update({n: dict(candidate=candidate, name=n, direction=direction.upper())
                                           for n in names})

    for a, m, width, driver in LINKS:
        for candidate, name in (("ACT20", a), ("MXU20", m)):
            port(candidate, name, "output" if candidate == driver else "input", width)
    for name, direction, width, owner in EXTERNAL:
        for candidate in (views if owner == "both" else [owner]):
            port(candidate, name, direction, width)
    return contract, views


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.views = fixture()

    def graph(self):
        return build_graph(self.contract, self.views)

    def test_full_fixed_graph_and_complete_unique_incidence(self):
        graph = self.graph()
        self.assertEqual(graph["external_ports"], self.contract["external_ports"])
        self.assertEqual(len(graph["connections"]), 685)
        self.assertEqual(len(graph["nets"]), 2346)
        self.assertEqual(len(graph["incidence"]), 4694)
        self.assertEqual(graph["summary"]["macro_endpoints"], 3032)
        self.assertEqual(graph["summary"]["drivers"], 2346)
        self.assertEqual(graph["summary"]["sinks"], 2348)
        identities = [(e["candidate"], e["name"]) for e in graph["incidence"]]
        self.assertEqual(len(identities), len(set(identities)))
        self.assertTrue(all(len([e for e in n["endpoints"] if e["role"] == "driver"]) == 1
                            and n["sinks"] for n in graph["nets"]))
        self.assertEqual(sum(c["driver"]["candidate"] == "ACT20" for c in graph["connections"]), 640)

    def test_computing_is_one_driver_feedback_and_parent_output(self):
        net = next(n for n in self.graph()["nets"] if n["name"] == "external:computing")
        self.assertEqual((net["driver"]["candidate"], net["driver"]["name"]), ("MXU20", "computing"))
        self.assertEqual({(s["candidate"], s["name"]) for s in net["sinks"]},
                         {("ACT20", "r_use"), ("TOP", "computing")})

    def test_shared_clock_is_one_parent_driver_and_two_macro_sinks(self):
        net = next(n for n in self.graph()["nets"] if n["name"] == "external:clk")
        self.assertEqual(net["driver"]["candidate"], "TOP")
        self.assertEqual({s["candidate"] for s in net["sinks"]}, {"ACT20", "MXU20"})
        self.assertTrue(all(s["direction"] == "input" for s in net["sinks"]))

    def test_dictionary_order_cannot_zip_lef_rows_into_connections(self):
        first = self.graph()
        for view in self.views.values():
            view["bits"] = dict(reversed(list(view["bits"].items())))
            view["ports"] = dict(reversed(list(view["ports"].items())))
        self.assertEqual(self.graph(), first)
        bit10 = next(c for c in first["connections"] if c["group"] == "r_data->act_data" and c["offset"] == 10)
        self.assertEqual(bit10["driver"]["name"], "r_data[10]")
        self.assertEqual(bit10["sink"]["name"], "act_data[10]")

    def test_internal_aliases_and_constants_do_not_merge_physical_pins(self):
        self.views["MXU20"]["aliases"] = {"done": "pf_u"}
        self.views["MXU20"]["constants"] = {f"{p}[{i}]": "0" for p in ("a_addr", "b_addr") for i in (30, 31)}
        self.views["MXU20"]["ports"]["done"]["source_bits"] = [247]
        self.views["MXU20"]["ports"]["pf_u"]["source_bits"] = [247]
        graph = self.graph()
        nets = {n["name"]: n for n in graph["nets"]}
        for pin in ["done", "pf_u", "a_addr[30]", "a_addr[31]", "b_addr[30]", "b_addr[31]"]:
            self.assertEqual(nets["external:" + pin]["driver"]["name"], pin)
        self.assertTrue(graph["summary"]["boundary_wiring_only"])
        self.assertFalse(graph["summary"]["logical_aliases_merged"])
        self.assertFalse(graph["summary"]["constant_ports_merged"])

    def test_wrong_interface_direction_rejected(self):
        self.views["ACT20"]["ports"]["r_data"]["direction"] = "input"
        for name in self.views["ACT20"]["ports"]["r_data"]["bits"]:
            self.views["ACT20"]["bits"][name]["direction"] = "INPUT"
        with self.assertRaisesRegex(GraphError, "Wrong direction"):
            self.graph()

    def test_wrong_parent_direction_rejected(self):
        self.contract["external_ports"]["done"]["direction"] = "input"
        with self.assertRaisesRegex(GraphError, "Parent/macro shape mismatch"):
            self.graph()

    def test_missing_bit_row_rejected(self):
        del self.views["ACT20"]["bits"]["r_data[511]"]
        with self.assertRaisesRegex(GraphError, "Missing bit row"):
            self.graph()

    def test_short_declared_bit_list_rejected(self):
        self.views["MXU20"]["ports"]["act_data"]["bits"].pop()
        with self.assertRaisesRegex(GraphError, "LSB-first"):
            self.graph()

    def test_reversed_bit_list_rejected(self):
        self.views["ACT20"]["ports"]["r_data"]["bits"].reverse()
        with self.assertRaisesRegex(GraphError, "LSB-first"):
            self.graph()

    def test_unknown_connection_port_rejected(self):
        self.contract["connections"][0]["act_port"] = "missing"
        with self.assertRaisesRegex(GraphError, "Unknown connection group"):
            self.graph()

    def test_missing_contracted_port_rejected(self):
        names = self.views["ACT20"]["ports"].pop("ren")["bits"]
        for name in names:
            del self.views["ACT20"]["bits"][name]
        with self.assertRaisesRegex(GraphError, "Missing contracted port"):
            self.graph()

    def test_duplicate_connection_group_rejected(self):
        self.contract["connections"][1] = deepcopy(self.contract["connections"][0])
        with self.assertRaisesRegex(GraphError, "Duplicate connection group"):
            self.graph()

    def test_endpoint_cannot_belong_to_internal_and_parent_nets(self):
        self.contract["external_ports"]["r_grp"] = self.contract["external_ports"].pop("w_off")
        with self.assertRaisesRegex(GraphError, "already belongs to net"):
            self.graph()

    def test_unknown_view_bit_rejected(self):
        self.views["ACT20"]["bits"]["unexpected"] = {}
        with self.assertRaisesRegex(GraphError, "unknown or omitted bit rows"):
            self.graph()

    def test_unassigned_extra_port_rejected(self):
        self.views["ACT20"]["ports"]["unexpected"] = dict(direction="input", width=1, bits=["unexpected"])
        self.views["ACT20"]["bits"]["unexpected"] = {}
        with self.assertRaisesRegex(GraphError, "Unassigned or unknown macro endpoints"):
            self.graph()

    def test_unknown_parent_port_rejected(self):
        self.contract["external_ports"]["missing"] = self.contract["external_ports"].pop("done")
        with self.assertRaisesRegex(GraphError, "Unknown or ambiguous parent port"):
            self.graph()

    def test_unknown_shared_same_name_port_rejected(self):
        self.views["ACT20"]["ports"]["rst"] = dict(direction="input", width=1, bits=["rst"])
        self.views["ACT20"]["bits"]["rst"] = {}
        with self.assertRaisesRegex(GraphError, "Unknown or ambiguous parent port"):
            self.graph()

    def test_connection_width_change_rejected(self):
        self.contract["connections"][0]["width"] = 3
        with self.assertRaisesRegex(GraphError, "Wrong connection width"):
            self.graph()

    def test_view_width_change_rejected(self):
        port = self.views["ACT20"]["ports"]["ren"]
        port.update(width=1, bits=["ren"])
        self.views["ACT20"]["bits"].pop("ren[0]")
        self.views["ACT20"]["bits"].pop("ren[1]")
        self.views["ACT20"]["bits"]["ren"] = {}
        with self.assertRaisesRegex(GraphError, "Width mismatch"):
            self.graph()

    def test_unverified_identity_rejected(self):
        self.contract["connections"][0]["exact_bit_identity"] = False
        with self.assertRaisesRegex(GraphError, "Unverified bit identity"):
            self.graph()

    def test_row_identity_and_direction_must_match_port(self):
        for field, value in [("name", "other"), ("candidate", "MXU20"), ("direction", "OUTPUT")]:
            with self.subTest(field=field):
                contract, views = fixture()
                views["ACT20"]["bits"]["ren[0]"][field] = value
                with self.assertRaises(GraphError):
                    build_graph(contract, views)

    def test_inputs_not_mutated_or_output_parent_definition_aliased(self):
        before = deepcopy((self.contract, self.views))
        graph = self.graph()
        self.assertEqual((self.contract, self.views), before)
        graph["external_ports"]["we"]["width"] = 99
        self.assertEqual(self.contract["external_ports"]["we"]["width"], 4)


if __name__ == "__main__":
    unittest.main()
