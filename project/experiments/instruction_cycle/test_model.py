import unittest
from dataclasses import replace

from model import Operation, Receiver, Resource, Service, simulate


def edges(result, kind):
    return [(event["cycle"], event["op"]) for event in result["events"] if event["event"] == kind]


class InstructionCycleTest(unittest.TestCase):
    def test_operator_conflict_and_initiation_interval(self):
        programs = {"B": [Operation("b0", "op"), Operation("b1", "op")],
                    "A": [Operation("a0", "op"), Operation("a1", "op")]}
        services = {"op": Service("vector", latency=4, interval=2)}
        result = simulate(programs, services, {"vector": Resource(("A", "B"), 2)}, {})
        self.assertEqual(edges(result, "issue"), [(0, "a0"), (2, "b0"), (5, "a1"), (7, "b1")])
        self.assertEqual(result["last_cycle"], 11)

    def test_shared_port_and_disjoint_banks(self):
        programs = {"A": [Operation("a", "bank0")], "B": [Operation("b", "bank1")]}
        resources = {"shared": Resource(("A", "B"), 1), "bank1": Resource(("B",), 1)}
        shared = {"bank0": Service("shared", 3, 1), "bank1": Service("shared", 3, 1)}
        independent = dict(shared, bank1=Service("bank1", 3, 1))
        self.assertEqual(edges(simulate(programs, shared, resources, {}), "issue"), [(0, "a"), (4, "b")])
        self.assertEqual(dict((op, edge) for edge, op in edges(simulate(programs, independent, resources, {}), "issue")),
                         {"a": 0, "b": 0})

    def test_wait_blocks_later_pc_and_ack_is_registered(self):
        programs = {"A": [Operation("write", "xfer")],
                    "B": [Operation("read", "read", ("write",)), Operation("independent", "read")]}
        services = {"xfer": Service("link", 2, 1, "dst"), "read": Service("alu", 1, 1)}
        resources = {"link": Resource(("A",), 1), "alu": Resource(("B",), 1)}
        result = simulate(programs, services, resources, {"dst": Receiver(1, 3, ("link",))})
        self.assertEqual(edges(result, "service_done")[0], (2, "write"))
        self.assertEqual(edges(result, "ack"), [(6, "write")])
        self.assertEqual(edges(result, "issue"), [(0, "write"), (7, "read"), (9, "independent")])

    def test_explicit_port_order_and_no_same_edge_refill(self):
        services = {"a": Service("ra", 1, 1, "sink"), "b": Service("rb", 1, 1, "sink")}
        resources = {"ra": Resource(("A",), 1), "rb": Resource(("B",), 1)}
        receivers = {"sink": Receiver(1, 2, ("ra", "rb"))}
        for name in ("first", "z-last"):
            programs = {"B": [Operation("middle", "b")], "A": [Operation(name, "a")]}
            result = simulate(programs, services, resources, receivers)
            self.assertEqual(edges(result, "enqueue"), [(2, name), (5, "middle")])
            self.assertEqual(edges(result, "ack"), [(4, name), (7, "middle")])

    def test_fixed_priority(self):
        programs = {"B": [Operation("b", "op")], "A": [Operation("a", "op"), Operation("a1", "op")]}
        services = {"op": Service("unit", 1, 1)}
        result = simulate(programs, services, {"unit": Resource(("A", "B"), 1, "fixed")}, {})
        self.assertEqual(edges(result, "issue"), [(0, "a"), (2, "a1"), (4, "b")])

    def test_stalled_output_holds_owner_but_unrelated_block_runs(self):
        programs = {"A": [Operation("a0", "copy"), Operation("a1", "copy")],
                    "B": [Operation("b", "op", ("a0",))],
                    "C": [Operation("c", "op2")]}
        services = {"copy": Service("link", 1, 1, "sink"), "op": Service("b_alu", 1, 1),
                    "op2": Service("c_alu", 2, 1)}
        resources = {"link": Resource(("A",), 1), "b_alu": Resource(("B",), 1),
                     "c_alu": Resource(("C",), 1)}
        result = simulate(programs, services, resources, {"sink": Receiver(1, 5, ("link",))})
        self.assertEqual(dict((op, edge) for edge, op in edges(result, "issue")),
                         {"a0": 0, "c": 0, "a1": 8, "b": 8})

    def test_invalid_route_and_deadlock_fail(self):
        resources = {"r": Resource(("A",), 1)}
        with self.assertRaisesRegex(ValueError, "invalid service"):
            simulate({"A": [Operation("op", "missing")]}, {}, resources, {})
        programs = {"A": [Operation("earlier", "op", ("later",)), Operation("later", "op")]}
        with self.assertRaisesRegex(ValueError, "deadlock.*earlier"):
            simulate(programs, {"op": Service("r", 1, 1)}, resources, {})

    def test_rejects_noninteger_and_nonpositive_timing_and_capacity(self):
        programs = {"A": [Operation("a", "op")]}
        service = Service("r", 1, 1, "rx")
        resource = Resource(("A",), 1)
        receiver = Receiver(1, 1, ("r",))
        for value in (0, -1, 1.5, True, float("nan")):
            for field in ("latency", "interval"):
                with self.subTest(config="service", field=field, value=value):
                    with self.assertRaisesRegex(ValueError, "invalid service"):
                        simulate(programs, {"op": replace(service, **{field: value})},
                                 {"r": resource}, {"rx": receiver})
            with self.subTest(config="resource", field="slots", value=value):
                with self.assertRaisesRegex(ValueError, "invalid resource"):
                    simulate(programs, {"op": service}, {"r": replace(resource, slots=value)}, {"rx": receiver})
            for field in ("depth", "latency"):
                with self.subTest(config="receiver", field=field, value=value):
                    with self.assertRaisesRegex(ValueError, "invalid receiver"):
                        simulate(programs, {"op": service}, {"r": resource},
                                 {"rx": replace(receiver, **{field: value})})

    def test_jumps_over_idle_cycles(self):
        programs = {"A": [Operation("op", "long")]}
        result = simulate(programs, {"long": Service("r", 10**9, 1)}, {"r": Resource(("A",), 1)}, {})
        self.assertEqual(edges(result, "complete"), [(10**9, "op")])


if __name__ == "__main__":
    unittest.main()
