"""Independent calendar/capacity boundaries using tiny synthetic witnesses."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("service_audit", Path(__file__).with_name("receive_service.py"))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def node(key, start=0, duration=2, deps=(), resource="bank", amount=1):
    return dict(id=key, start=start, end=start + duration, duration=duration, deps=list(deps),
                reservations=[dict(resource=resource, offset=0, duration=duration, amount=amount)])


class ServiceAuditTests(unittest.TestCase):
    def test_half_open_1RW(self):
        result = r.verify_intervals([node("a"), node("b", 2, deps=("a",))], {"bank": 1})
        self.assertEqual((result["makespan"], result["lower_bound"]), (4, 4))

    def test_double_booked_bank(self):
        with self.assertRaisesRegex(AssertionError, "resource overlap/capacity"):
            r.verify_intervals([node("a"), node("b", 1)], {"bank": 1})

    def test_missing_or_unpublished_dependency(self):
        with self.assertRaisesRegex(AssertionError, "known non-self"):
            r.verify_intervals([node("a", deps=("lost",))], {"bank": 1})
        with self.assertRaisesRegex(AssertionError, "dependency publication"):
            r.verify_intervals([node("a"), node("b", 1, deps=("a",))], {"bank": 2})

    def test_FIFO_credit_peak(self):
        with self.assertRaisesRegex(AssertionError, "resource overlap/capacity"):
            r.verify_intervals([node("a", resource="FIFO", amount=1025), node("b", resource="FIFO", amount=1024)], {"FIFO": 2048})

    def test_resident_capacity(self):
        allocations = [dict(name="old", bank="R", bytes=16, resident=[0, 4]),
                       dict(name="new", bank="R", bytes=16, resident=[0, 4]),
                       dict(name="aux", bank="R", bytes=1, resident=[0, 4])]
        with self.assertRaisesRegex(AssertionError, "resident bank capacity"):
            r.verify_allocations(allocations, {"R": 32}, 4)

    def test_shadow_address_alias_rejected(self):
        allocations = [dict(name="old", bank="R", bytes=16, address=0, resident=[0, 4]),
                       dict(name="new", bank="R", bytes=16, address=8, resident=[0, 4])]
        with self.assertRaisesRegex(AssertionError, "resident address overlap"):
            r.verify_allocations(allocations, {"R": 32}, 4)

    def test_outside_reservation_rejected(self):
        a = node("a")
        a["reservations"][0]["offset"] = 1
        with self.assertRaisesRegex(AssertionError, "reservation contained"):
            r.verify_intervals([a], {"bank": 1})

    def test_wide_merges_are_not_free(self):
        work, read, write, sfu = r.math_work({"operation": "new_state_completeK_output"}, {"tile": 16, "state_bits": 32})
        self.assertEqual((work, read, write, sfu), (2048 * (15 + 14 * 10 + 10) + 160, 8192 + 256, 128, 0))

    def test_norm_gamma_and_requant_separate_memory(self):
        c = {"tile": 16, "state_bits": 32}
        self.assertEqual(r.math_work({"operation": "norm_gamma"}, c), (128 * (155 + 265 + 20), 800, 512, 0))
        self.assertEqual(r.math_work({"operation": "fresh_A8K128"}, c), (3840, 512, 129, 0))

    def test_unknown_operation_cannot_use_default_cost(self):
        with self.assertRaisesRegex(AssertionError, "unqualified math operation"):
            r.math_work({"operation": "divide_for_free"}, {"tile": 16, "state_bits": 32})

    def test_full_row_and_R_shadow_slots(self):
        slots = r.expected_slots({"tile": 32, "state_bits": 32})
        self.assertEqual(slots["V.X16"], ("V", 0, 5120))
        self.assertEqual(slots["source.mixed"], ("S0", 0, 25600))
        self.assertEqual(slots["R.new_shadow"], ("S4", 0, 16384))
        self.assertNotIn("R.new", slots)

    def test_label_only_lane_partition_is_identical(self):
        for suffix in ("2_6", "4_4", "6_2"):
            self.assertEqual(r.lane_partition("shared" + suffix), r.lane_partition("split" + suffix))

    def test_overlap_negative_keeps_dependency_ready(self):
        a = node("a", duration=10, resource="LANE:0")
        b = node("b", start=10, duration=10, resource="LANE:0")
        a.update(kind="math", meta={"domain": "V"})
        b.update(kind="math", meta={"domain": "R"})
        changed, label = r.mutate_witness({"nodes": [a, b]}, "overlap")
        self.assertEqual(label, "resource overlap/capacity")
        with self.assertRaisesRegex(AssertionError, label):
            r.verify_intervals(changed["nodes"], {"LANE:0": 1})


if __name__ == "__main__":
    unittest.main()
