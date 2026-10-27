import unittest

from audit import Invalid
from obstruction_coverage import covered, inspect


class CoverageControls(unittest.TestCase):
    def test_union_of_two_rectangles(self):
        self.assertTrue(covered((0, 0, 10, 10), [(0, 0, 5, 10), (5, 0, 10, 10)]))

    def test_tiny_hole_is_not_rounded_away(self):
        self.assertFalse(covered((0, 0, 10, 10), [(0, 0, 4, 10), (5, 0, 10, 10)]))

    def test_overlap_and_boundary_touch(self):
        self.assertTrue(covered((0, 0, 10, 10), [(0, 0, 7, 10), (5, 0, 10, 10)]))
        self.assertFalse(covered((0, 0, 10, 10), [(-5, 0, 0, 10), (10, 0, 15, 10)]))

    def test_equal_area_does_not_prove_coverage(self):
        self.assertFalse(covered((0, 0, 10, 10), [(0, 0, 10, 5), (0, 0, 10, 5)]))

    def test_same_net_pin_window_only(self):
        source = [["# block-v1-odb-geometry/1 dbu_per_um=2000"], ["# NET n1 64"],
                  ["# PORT n1 64"], ["n1", "metal10", "wire", "0", "0", "10", "10"]]
        lef = [["obstruction", "metal10", "0", "0", "5", "10"],
               ["box", "d", "metal10", "5", "0", "10", "10"]]
        self.assertTrue(inspect(source, lef)["passed"])
        lef[1][1] = "other_net"
        self.assertEqual(inspect(source, lef)["uncovered_count"], 1)

    def test_wrong_layer_and_missing_metadata(self):
        source = [["# block-v1-odb-geometry/1 dbu_per_um=2000"], ["# NET n1 64"],
                  ["n1", "metal9", "wire", "0", "0", "10", "10"]]
        lef = [["obstruction", "metal10", "0", "0", "10", "10"]]
        self.assertFalse(inspect(source, lef)["passed"])
        with self.assertRaises(Invalid):
            inspect(source[1:], lef)

    def test_large_failure_counts_all_shapes_with_bounded_examples(self):
        source = [["# block-v1-odb-geometry/1 dbu_per_um=2000"], ["# NET n1 64"]]
        source += [["n1", "metal9", "wire", "0", "0", "10", "10"] for _ in range(150)]
        result = inspect(source, [["obstruction", "metal10", "0", "0", "10", "10"]])
        self.assertFalse(result["passed"])
        self.assertEqual(result["uncovered_count"], 150)
        self.assertEqual(len(result["uncovered_examples"]), 100)

    def test_streaming_factory_sees_port_metadata_after_geometry(self):
        source = [["# block-v1-odb-geometry/1 dbu_per_um=2000"], ["# NET n1 64"],
                  ["n1", "metal10", "wire", "0", "0", "10", "10"], ["# PORT n1 64"]]
        calls = []
        def factory():
            calls.append(1)
            return iter(source)
        lef = [["obstruction", "metal10", "0", "0", "5", "10"], ["box", "d", "metal10", "5", "0", "10", "10"]]
        self.assertTrue(inspect(factory, lef)["passed"])
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
