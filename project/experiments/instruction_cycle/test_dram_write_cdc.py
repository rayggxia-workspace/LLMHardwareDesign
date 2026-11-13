import unittest
from fractions import Fraction

from check_dram_write_cdc import HOST_PERIOD, DDR_PERIOD
from dma_ddr import DmaPort, Fence, TimedBackend, Transfer


class DramWriteCdcTest(unittest.TestCase):
    def test_crossing_fixture_uses_exact_300_mhz(self):
        self.assertEqual(HOST_PERIOD * 3, 10000)
        self.assertEqual((HOST_PERIOD * 189) / DDR_PERIOD, 1000)
        self.assertEqual((HOST_PERIOD * 189 - 173) // DDR_PERIOD, 999)
        self.assertIsInstance(HOST_PERIOD, Fraction)

    def test_pending_host_delivery_cannot_release_a_fence(self):
        class CrossingBackend(TimedBackend):
            def __init__(self):
                super().__init__(1, 3)
                self.crossing = []

            @property
            def idle(self):
                return super().idle and not self.crossing

            def completions(self, cycle):
                visible = [key for edge, key in self.crossing if edge == cycle]
                self.crossing = [(edge, key) for edge, key in self.crossing if edge != cycle]
                self.crossing.extend((cycle + 3, key) for key in super().completions(cycle))
                return visible

        new = bytes([77]) * 64
        port = DmaPort(CrossingBackend(), 3, 2, 1, {0: bytes(64)})
        offers = {0: Transfer("write", 0, 64, True, new), 1: Fence("fence"),
                  2: Transfer("after", 0, 64)}
        results = {}
        for cycle in range(25):
            _, response = port.step(cycle, offers.get(cycle))
            if cycle == 4:  # Peer completed; the completion is still in crossing.
                self.assertFalse(port.backend.idle)
                self.assertFalse(port.drained)
                self.assertEqual(port.memory[0], bytes(64))
            if response:
                results[response.tag] = (cycle, response.data)
        self.assertEqual(results, {"write": (9, b""), "fence": (11, b""), "after": (20, new)})
        self.assertTrue(port.drained)
