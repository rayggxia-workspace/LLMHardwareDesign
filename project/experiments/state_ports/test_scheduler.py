"""Independent integer-start enumeration and behavioral scheduler checks."""
from copy import deepcopy
import random
import unittest

from scheduler import POLICIES, exact_schedule, schedule, validate_schedule


def task(name, duration, resources=None, deps=None):
    return {"id": name, "duration": duration, "deps": deps or [], "resources": resources or {}}


def integer_start_enumeration(tasks, capacities):
    """Test-only oracle enumerating integer starts, independent of event DP.

    Assigns tasks in an independently constructed topological order and checks
    resource occupancy at each integer slot. Serial execution gives a finite
    sum(duration) upper bound under this test's resource/precedence-only model.
    It never requires starting all tasks that currently fit.
    """
    horizon = sum(t["duration"] for t in tasks)
    remaining = {t["id"]: t for t in tasks}
    order, known = [], set()
    while remaining:
        eligible = [t for t in tasks if t["id"] in remaining and set(t["deps"]) <= known]
        if not eligible:
            raise ValueError("enumeration fixture is cyclic")
        row = eligible[0]
        order.append(row)
        known.add(row["id"])
        del remaining[row["id"]]
    usage = {r: [0] * horizon for r in capacities}
    finishes = {}
    best = horizon

    def assign(position, partial_end):
        nonlocal best
        if position == len(order):
            best = min(best, partial_end)
            return
        row = order[position]
        release = max((finishes[d] for d in row["deps"]), default=0)
        # Searching only strict improvements is safe: best starts with the
        # independently known feasible serial bound, not an event-oracle value.
        for start in range(release, best - row["duration"]):
            end = start + row["duration"]
            if any(usage[r][tick] + amount > capacities[r]
                   for r, amount in row["resources"].items() for tick in range(start, end)):
                continue
            for r, amount in row["resources"].items():
                for tick in range(start, end):
                    usage[r][tick] += amount
            finishes[row["id"]] = end
            assign(position + 1, max(partial_end, end))
            del finishes[row["id"]]
            for r, amount in row["resources"].items():
                for tick in range(start, end):
                    usage[r][tick] -= amount

    assign(0, 0)
    return best


def idle_counterexample():
    return [task("A", 5, {"x": 1}), task("B", 1, {"y": 1}),
            task("C", 1, {"x": 1}, ["B"]), task("D", 5, {"y": 1}, ["C"])], {"x": 1, "y": 1}


class SchedulerTests(unittest.TestCase):
    def assert_feasible(self, tasks, caps, result):
        report = validate_schedule(tasks, caps, result)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["makespan"], result["makespan"])

    def test_empty(self):
        for policy in POLICIES:
            out = schedule([], {}, policy)
            self.assertEqual(out["makespan"], 0)
            self.assertEqual(out["events"], [])
            self.assert_feasible([], {}, out)
        self.assertEqual(exact_schedule([], {})["makespan"], 0)

    def test_half_open_release_at_same_time(self):
        rows = [task("first", 2, {"port": 1}), task("second", 3, {"port": 1}, ["first"])]
        for policy in POLICIES:
            out = schedule(rows, {"port": 1}, policy)
            self.assertEqual(out["makespan"], 5)
            self.assert_feasible(rows, {"port": 1}, out)

    def test_atomic_multiple_resources_and_capacity_units(self):
        rows = [task("dma", 3, {"src": 1, "dst": 1}), task("dst-read", 2, {"dst": 1}),
                task("src-read", 2, {"src": 1})]
        for policy in POLICIES:
            out = schedule(rows, {"src": 1, "dst": 1}, policy)
            self.assert_feasible(rows, {"src": 1, "dst": 1}, out)
            self.assertEqual(out["makespan"], 5)
        rows = [task("a", 2, {"p": 1}), task("b", 2, {"p": 1}),
                task("c", 1, {"p": 2}, ["a", "b"])]
        out = schedule(rows, {"p": 2})
        self.assertEqual(out["makespan"], 3)
        self.assertEqual(validate_schedule(rows, {"p": 2}, out)["resource_peaks"], {"p": 2})

    def test_fifo_uses_ready_arrival_not_only_input_index(self):
        rows = [task("child", 1, {"p": 1}, ["B"]), task("B", 1),
                task("A", 3, {"p": 1}), task("old-ready", 1, {"p": 1})]
        out = schedule(rows, {"p": 1}, "fifo")
        starts = {e["id"]: e["start"] for e in out["events"]}
        self.assertEqual(starts["old-ready"], 3)
        self.assertEqual(starts["child"], 4)
        self.assert_feasible(rows, {"p": 1}, out)

    def test_critical_uses_duration_weighted_successor_path(self):
        rows = [task("a", 1, {"p": 1}), task("b", 3, {"p": 1}),
                task("tail", 5, {"q": 1}, ["a"])]
        self.assertEqual(schedule(rows, {"p": 1, "q": 1}, "critical")["makespan"], 6)
        self.assertEqual(schedule(rows, {"p": 1, "q": 1}, "longest")["makespan"], 9)

    def test_ties_use_input_order_and_do_not_mutate(self):
        rows = [task("z", 2, {"p": 1}), task("a", 2, {"p": 1})]
        rows[0]["metadata"] = {"phase": "read"}
        caps = {"p": 1}
        before = deepcopy((rows, caps))
        for policy in POLICIES:
            first = schedule(rows, caps, policy)
            self.assertEqual(first, schedule(rows, caps, policy))
            self.assertEqual(first["events"][0]["id"], "z")
        exact = exact_schedule(rows, caps)
        self.assertEqual(exact, exact_schedule(rows, caps))
        self.assertEqual((rows, caps), before)

    def test_resource_free_tasks_and_unsorted_dag(self):
        rows = [task("last", 2, {}, ["first"]), task("first", 3), task("parallel", 4)]
        for policy in POLICIES:
            out = schedule(rows, {}, policy)
            self.assertEqual(out["makespan"], 5)
            self.assert_feasible(rows, {}, out)
        self.assertEqual(exact_schedule(rows, {})["makespan"], 5)

    def test_non_delay_heuristics_all_lose_to_deliberate_idle(self):
        rows, caps = idle_counterexample()
        exact = exact_schedule(rows, caps)
        self.assert_feasible(rows, caps, exact)
        self.assertTrue(exact["proven_optimal"])
        self.assertEqual(exact["makespan"], 7)
        self.assertEqual(exact["bounds"]["lower_bound"], 7)
        starts = {e["id"]: e["start"] for e in exact["events"]}
        self.assertEqual(starts, {"B": 0, "C": 1, "A": 2, "D": 2})
        for policy in POLICIES:
            out = schedule(rows, caps, policy)
            self.assert_feasible(rows, caps, out)
            self.assertFalse(out["proven_optimal"])
            self.assertEqual(out["makespan"], 11)
        self.assertEqual(integer_start_enumeration(rows, caps), 7)

    def test_exact_matches_independent_integer_start_enumeration(self):
        fixtures = [([], {}), ([task("single", 3)], {}),
                    ([task("a", 2, {"p": 2}), task("b", 2, {"p": 1}),
                      task("c", 1, {"p": 1}, ["b"])], {"p": 2})]
        rng = random.Random(27001)
        for case in range(18):
            caps = {"p": 2, "q": 2}
            rows = []
            for i in range(4):
                demands = {r: rng.randint(1, 2) for r in caps if rng.random() < .65}
                deps = [str(j) for j in range(i) if rng.random() < .25]
                rows.append(task(str(i), rng.randint(1, 3), demands, deps))
            fixtures.append((rows, caps))
        for case, (rows, caps) in enumerate(fixtures):
            with self.subTest(case=case):
                exact = exact_schedule(rows, caps)
                self.assertEqual(exact["makespan"], integer_start_enumeration(rows, caps))
                self.assert_feasible(rows, caps, exact)
                for policy in POLICIES:
                    result = schedule(rows, caps, policy)
                    self.assert_feasible(rows, caps, result)
                    self.assertGreaterEqual(result["makespan"], exact["makespan"])

    def test_nine_task_oracle_and_guard(self):
        rows = [task(str(i), 1, {"p": 1}) for i in range(9)]
        out = exact_schedule(rows, {"p": 1})
        self.assertEqual(out["makespan"], 9)
        self.assert_feasible(rows, {"p": 1}, out)
        with self.assertRaises(ValueError):
            exact_schedule(rows + [task("10", 1, {"p": 1})], {"p": 1})
        with self.assertRaises(RuntimeError):
            exact_schedule([task("a", 1)], {}, max_states=1)

    def test_rejects_invalid_problem(self):
        invalid = [
            ([task("a", 0)], {}), ([task("a", True)], {}),
            ([task("a", 1)], {"p": 0}), ([task("a", 1)], {"p": True}),
            ([task("a", 1, {"missing": 1})], {"p": 1}),
            ([task("a", 1, {"p": 0})], {"p": 1}),
            ([task("a", 1, {"p": -1})], {"p": 1}),
            ([task("a", 1, {"p": True})], {"p": 1}),
            ([task("a", 1, {"p": 2})], {"p": 1}),
            ([task("a", 1, {}, ["missing"])], {}),
            ([task("a", 1, {}, ["a"])], {}),
            ([task("a", 1), task("a", 1)], {}),
            ([task("a", 1), task("b", 1, {}, ["a", "a"])], {}),
            ([task("a", 1, {}, ["b"]), task("b", 1, {}, ["a"])], {}),
        ]
        for rows, caps in invalid:
            for function in (schedule, exact_schedule):
                with self.subTest(rows=rows, caps=caps, function=function.__name__):
                    with self.assertRaises(ValueError):
                        function(rows, caps)
            self.assertFalse(validate_schedule(rows, caps, {"events": [], "makespan": 0})["valid"])
        with self.assertRaises(ValueError):
            schedule([], {}, policy="unknown")

    def test_validator_rejects_capacity_dependency_and_makespan(self):
        rows = [task("a", 3, {"p": 1}), task("b", 2, {"p": 1}, ["a"])]
        out = {"makespan": 999, "events": [{"id": "a", "start": 0, "end": 3},
                                            {"id": "b", "start": 1, "end": 3}]}
        report = validate_schedule(rows, {"p": 1}, out)
        self.assertFalse(report["valid"])
        self.assertTrue(any("dependency" in e for e in report["errors"]))
        self.assertTrue(any("capacity" in e for e in report["errors"]))
        self.assertTrue(any("makespan" in e for e in report["errors"]))

    def test_validator_rejects_ids_duration_and_bad_times(self):
        rows = [task("a", 3), task("b", 2)]
        invalid_events = [
            [{"id": "a", "start": 0, "end": 2}],
            [{"id": "a", "start": 0, "end": 3}, {"id": "a", "start": 3, "end": 6}],
            [{"id": "alien", "start": 0, "end": 3}],
            [{"id": "a", "start": -1, "end": 2}],
            [{"id": "a", "start": True, "end": 4}],
            [{"id": "a", "start": 0.0, "end": 3}],
            [{"id": "a", "start": 3, "end": 3}],
        ]
        for events in invalid_events:
            self.assertFalse(validate_schedule(rows, {}, {"events": events, "makespan": 3})["valid"])
        self.assertFalse(validate_schedule(rows, {}, [])['valid'])


if __name__ == "__main__":
    unittest.main()
