import unittest

from port_oracle import Buffer, Task, event_schedule, exact_cycles, fixtures, validate_schedule


class PortTests(unittest.TestCase):
    def test_hand_exact_cases_and_independent_schedule_audit(self):
        expected = {"colocated": 14, "separated": 10, "greedy_counterexample": 12,
                    "dma_two_ends": 6, "capacity_exact_fit": 2, "capacity_impossible": None}
        for name, (tasks, buffers, capacities) in fixtures().items():
            with self.subTest(name=name):
                optimal = exact_cycles(tasks, buffers, capacities)
                self.assertEqual(optimal, expected[name])
                schedule = event_schedule(tasks, buffers, capacities)
                if schedule["status"] == "ok":
                    self.assertTrue(validate_schedule(tasks, schedule, buffers, capacities))
                    self.assertGreaterEqual(schedule["makespan"], optimal)
                else:
                    self.assertEqual(name, "capacity_impossible")

    def test_greedy_is_not_optimality_oracle(self):
        tasks, buffers, capacities = fixtures()["greedy_counterexample"]
        self.assertEqual(event_schedule(tasks)["makespan"], 16)
        self.assertEqual(exact_cycles(tasks), 12)

    def test_rw_direction_and_half_open_cycle_boundary(self):
        shared = [Task("read", 2, ("RW",)), Task("write", 2, ("RW",))]
        split = [Task("read", 2, ("R",)), Task("write", 2, ("W",))]
        self.assertEqual(exact_cycles(shared), 4)
        self.assertEqual(exact_cycles(split), 2)
        self.assertTrue(validate_schedule(shared, event_schedule(shared)))

    def test_independent_validator_rejects_overlap_and_liveness(self):
        tasks = [Task("a", 2, ("P",)), Task("b", 2, ("P",))]
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_schedule(tasks, {"events": [{"task": "a", "start": 0, "end": 2},
                                                 {"task": "b", "start": 1, "end": 3}]})
        tasks, buffers, _ = fixtures()["capacity_exact_fit"]
        with self.assertRaisesRegex(ValueError, "capacity"):
            validate_schedule(tasks, event_schedule(tasks, buffers, {"SRAM": 8}), buffers, {"SRAM": 7})

    def test_retained_kv_remains_live_during_ephemeral_work(self):
        tasks = [Task("make", 1, ("P",)), Task("use", 1, ("P",), ("make",))]
        buffers = [Buffer("KV", 4, "SRAM", None, (), True), Buffer("tmp", 4, "SRAM", "make", ("use",))]
        self.assertIsNone(exact_cycles(tasks, buffers, {"SRAM": 7}))
        self.assertEqual(exact_cycles(tasks, buffers, {"SRAM": 8}), 2)

    def test_invalid_graphs_and_noninteger_cycles_rejected(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            event_schedule([Task("a", 1, ("P",), ("b",)), Task("b", 1, ("P",), ("a",))])
        with self.assertRaises(ValueError):
            exact_cycles([Task("a", True, ("P",))])
        with self.assertRaises(ValueError):
            exact_cycles([Task("a", 1, ("P",)), Task("b", 1, ("P",), ("a", "a"))])


if __name__ == "__main__":
    unittest.main()
