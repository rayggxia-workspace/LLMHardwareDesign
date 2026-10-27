"""Native model metadata receiver controls; all fixtures are synthetic."""
from pathlib import Path
import tempfile
import unittest

from audit import Invalid
from native_lib_inventory import receive


class ModelInventoryControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.ports = {"clk": "input", "d": "input", "q": "output"}
        (self.folder / "model-ports.tsv").write_text("clk\tinput\t0\nd\tinput\t0\nq\toutput\t0\nVDD\tinput\t0\nVSS\tinput\t0\n")
        (self.folder / "model-arc-groups.tsv").write_text("0\td\tq\tCELL d -> q combinational\t0\t\t2\n")
        (self.folder / "model-arcs.tsv").write_text("0\t0\trise\trise\n0\t1\tfall\tfall\n")

    def test_complete_metadata_keeps_ordinary_supply_role(self):
        result = receive(self.folder, self.ports)
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["transition_arc_count"], 2)
        self.assertFalse(result["ports"]["VDD"]["is_power_ground"])
        self.assertEqual(result["supply_arc_groups"], [])
        self.assertFalse(result["flat_abstract_boundary_qualified"])

    def test_missing_transition_and_unknown_group_rejected(self):
        for text in ("0\t0\trise\trise\n", "1\t0\trise\trise\n0\t1\tfall\tfall\n"):
            (self.folder / "model-arcs.tsv").write_text(text)
            with self.assertRaises(Invalid):
                receive(self.folder, self.ports)

    def test_supply_arc_is_reported_not_silently_discarded(self):
        (self.folder / "model-arc-groups.tsv").write_text("0\tVDD\tq\tCELL VDD -> q combinational\t0\t\t2\n")
        self.assertEqual(receive(self.folder, self.ports)["supply_arc_groups"], ["0"])

    def test_native_null_source_group_is_preserved_as_unresolved_role(self):
        (self.folder / "model-arc-groups.tsv").write_text("0\t__NO_FROM_PIN__\tclk\t__NO_FROM_PIN__ -> clk native-null-from-role-unresolved\t0\t\t2\n")
        result = receive(self.folder, self.ports)
        self.assertFalse(result["native_role_metadata_complete"])
        self.assertEqual(result["group_count"], 1)

    def test_wrong_signal_direction_rejected(self):
        p = self.folder / "model-ports.tsv"
        p.write_text(p.read_text().replace("d\tinput", "d\toutput"))
        with self.assertRaisesRegex(Invalid, "signal pins"):
            receive(self.folder, self.ports)

    def test_typed_power_ground_roles_are_distinct_from_ordinary_inputs(self):
        p = self.folder / "model-ports.tsv"
        p.write_text(p.read_text().replace("VDD\tinput\t0", "VDD\tpower\t1").replace("VSS\tinput\t0", "VSS\tground\t1"))
        self.assertTrue(receive(self.folder, self.ports)["ports"]["VDD"]["is_power_ground"])
        p.write_text(p.read_text().replace("VDD\tpower\t1", "VDD\tground\t1"))
        with self.assertRaisesRegex(Invalid, "supply role"):
            receive(self.folder, self.ports)


if __name__ == "__main__":
    unittest.main()
