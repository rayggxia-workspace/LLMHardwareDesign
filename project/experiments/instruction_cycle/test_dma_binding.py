import unittest

from check_dma_ddr import coupled
from dma_ddr import DmaPort, Fence, TimedBackend, Transfer
from model import DmaBinding, Operation, Resource, Service, simulate


class DmaBindingTest(unittest.TestCase):
    def test_compute_and_dma_share_one_clock(self):
        self.assertEqual(coupled(TimedBackend(2, 2, 7, 3, 1), True)["last_cycle"], 32)

    def test_simultaneous_offers_use_explicit_port_priority(self):
        memory = {0: bytes(64), 64: bytes(64)}
        for programs in ({"A": [Operation("first", "a")], "B": [Operation("second", "b")]},
                         {"B": [Operation("second", "b")], "A": [Operation("first", "a")]}):
            port = DmaPort(TimedBackend(1, 2), 1, 1, 1, memory)
            binding = DmaBinding(port, {"first": Transfer("first", 0, 64),
                                        "second": Transfer("second", 64, 64)}, ("b", "a"))
            result = simulate(programs, {"a": Service("a", 1, 1), "b": Service("b", 1, 1)},
                              {"a": Resource(("A",), 1), "b": Resource(("B",), 1)}, {}, binding)
            self.assertEqual([row["tag"] for row in result["events"] if row["event"] == "accept"],
                             ["second", "first"])

    def test_source_must_hold_offer_under_backpressure(self):
        port = DmaPort(TimedBackend(1, 2), 1, 1, 1, {0: bytes(64)})
        port.step(0, Transfer("first", 0, 64))
        self.assertFalse(port.step(1, Transfer("second", 0, 64))[0])
        with self.assertRaisesRegex(ValueError, "changed an unaccepted offer"):
            port.step(2)

    def test_fast_fence_cannot_bypass_older_slow_descriptor(self):
        port = DmaPort(TimedBackend(2, 3), 2, 2, 1)
        requests = {"write": Transfer("write", 0, 64, True, bytes([5]) * 64),
                    "fence": Fence("fence"), "read": Transfer("read", 0, 64)}
        result = simulate({"A": [Operation("write", "slow"), Operation("fence", "fast"), Operation("read", "fast")]},
                          {"slow": Service("slow", 9, 1), "fast": Service("fast", 1, 1)},
                          {"slow": Resource(("A",), 1), "fast": Resource(("A",), 2)}, {},
                          DmaBinding(port, requests, ("fast", "slow")))
        self.assertEqual([row["tag"] for row in result["events"] if row["event"] == "accept"],
                         ["write", "fence", "read"])
        self.assertEqual(result["dma_responses"]["read"], bytes([5]) * 64)

    def test_hung_backend_reports_bounded_failure(self):
        backend = TimedBackend(1, 200)
        port = DmaPort(backend, 1, 1, 1, {0: bytes(64)})
        with self.assertRaisesRegex(ValueError, "did not finish by cycle 20"):
            simulate({"A": [Operation("read", "dma")]}, {"dma": Service("r", 1, 1)},
                     {"r": Resource(("A",), 1)}, {},
                     DmaBinding(port, {"read": Transfer("read", 0, 64)}, ("r",), max_cycles=20))
