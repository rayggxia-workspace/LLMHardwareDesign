import unittest

from dma_ddr import DmaPort, Fence, TimedBackend, Transfer


OLD = bytes([0x11]) * 64
NEW = bytes([0x22]) * 64
OTHER = bytes([0x33]) * 64


def events(port, name, tag):
    return [row["cycle"] for row in port.events if row["event"] == name and row["tag"] == tag]


class DmaDdrTest(unittest.TestCase):
    def test_same_address_write_visibility_and_nonoverlapping_completion(self):
        port = DmaPort(TimedBackend(depth=4, latency=2, write_latency=9), queue_depth=4, credits=4,
                       response_depth=2, initial_memory={0: OLD, 64: OTHER})
        offers = {0: Transfer("write", 0, 64, write=True, data=NEW), 1: Transfer("other", 64, 64),
                  2: Transfer("raw", 0, 64)}
        retired = []
        for cycle in range(30):
            accepted, response = port.step(cycle, offer=offers.get(cycle), consume=cycle >= 19)
            if cycle in offers:
                self.assertTrue(accepted)
            if not events(port, "write_visible", "write"):
                self.assertEqual(port.memory[0], OLD)
            if response is not None:
                retired.append(response)
        self.assertEqual(port.memory[0], NEW)
        self.assertLess(events(port, "read_return", "other")[0], events(port, "write_visible", "write")[0])
        self.assertLess(events(port, "write_visible", "write")[0], events(port, "backend_accept", "raw")[0])
        self.assertLess(events(port, "write_visible", "write")[0], events(port, "retire", "write")[0])
        self.assertEqual([response.tag for response in retired], ["write", "other", "raw"])
        self.assertEqual([response.data for response in retired[1:]], [OTHER, NEW])
        self.assertTrue(port.drained)

    def test_fence_cannot_release_younger_issue_until_consumed(self):
        port = DmaPort(TimedBackend(depth=2, latency=2, write_latency=5), queue_depth=3, credits=2,
                       response_depth=2, initial_memory={0: OLD, 64: OTHER})
        offers = {0: Transfer("write", 0, 64, write=True, data=NEW), 1: Fence("fence"),
                  2: Transfer("younger", 64, 64)}
        responses = []
        for cycle in range(32):
            accepted, response = port.step(cycle, offer=offers.get(cycle), consume=cycle >= 12 and cycle != 13)
            if cycle in offers:
                self.assertTrue(accepted)
            if cycle < 12:
                self.assertFalse(port.drained)
            if response is not None:
                responses.append(response.tag)
        self.assertEqual(responses, ["write", "fence", "younger"])
        self.assertLessEqual(events(port, "write_visible", "write")[0], events(port, "fence_ready", "fence")[0])
        self.assertLess(events(port, "accept", "younger")[0], events(port, "retire", "fence")[0])
        self.assertLess(events(port, "retire", "fence")[0], events(port, "backend_accept", "younger")[0])
        self.assertTrue(port.drained)

    def test_single_burst_credit_handles_a_larger_descriptor_and_held_response(self):
        port = DmaPort(TimedBackend(depth=1, latency=3, accept_period=3, accept_phase=1),
                       queue_depth=1, credits=1, response_depth=1,
                       initial_memory={0: OLD, 64: NEW, 128: OTHER})
        large, younger = Transfer("large", 0, 128), Transfer("younger", 128, 64)
        retired = []
        first_accept = None
        for cycle in range(34):
            offer = large if cycle == 0 else younger if first_accept is None else None
            accepted, response = port.step(cycle, offer=offer, consume=cycle >= 18)
            if cycle == 0:
                self.assertTrue(accepted)
            elif accepted:
                first_accept = cycle
            if response is not None:
                retired.append(response)
        first_issue = events(port, "backend_accept", "large")
        first_returns = events(port, "read_return", "large")
        self.assertEqual(len(first_issue), 2)
        self.assertTrue(all(edge % 3 == 1 for edge in first_issue))
        self.assertLess(first_returns[0], first_issue[1])
        self.assertGreaterEqual(first_accept, events(port, "retire", "large")[0])
        self.assertEqual([(response.tag, response.data) for response in retired],
                         [("large", OLD + NEW), ("younger", OTHER)])
        self.assertTrue(port.drained)

    def test_duplicate_same_address_reads_keep_separate_transaction_identities(self):
        port = DmaPort(TimedBackend(depth=3, latency=3), queue_depth=3, credits=3,
                       response_depth=3, initial_memory={0: OLD})
        labels = ["r0", "r1", "r2"]
        received = []
        for cycle in range(22):
            offer = Transfer(labels[cycle], 0, 64) if cycle < len(labels) else None
            accepted, response = port.step(cycle, offer=offer)
            if offer:
                self.assertTrue(accepted)
            if response:
                received.append(response)
        self.assertEqual([(response.tag, response.data) for response in received], [(tag, OLD) for tag in labels])
        self.assertTrue(all(len(events(port, "backend_accept", tag)) == 1 for tag in labels))
        self.assertTrue(all(len(events(port, "read_return", tag)) == 1 for tag in labels))

    def test_full_backend_holds_the_oldest_offer_and_does_not_change_its_id(self):
        port = DmaPort(TimedBackend(depth=1, latency=4), queue_depth=3, credits=3,
                       response_depth=3, initial_memory={0: OLD, 64: NEW, 128: OTHER})
        for cycle in range(20):
            offer = Transfer(str(cycle), 64 * cycle, 64) if cycle < 3 else None
            port.step(cycle, offer=offer)
        blocked = [row for row in port.events if row["event"] == "backend_stall" and row["tag"] == "1"]
        self.assertTrue(blocked)
        self.assertEqual([(row["tag"], row["beat"], row["addr"]) for row in blocked],
                         [("1", 0, 64)] * len(blocked))
        self.assertLess(max(row["cycle"] for row in blocked), events(port, "backend_accept", "1")[0])
        self.assertLess(events(port, "backend_accept", "1")[0], events(port, "backend_accept", "2")[0])
        self.assertTrue(port.drained)

    def test_invalid_range_and_reused_identity_are_rejected(self):
        port = DmaPort(TimedBackend(depth=2, latency=2), queue_depth=2, credits=2,
                       response_depth=2, initial_memory={0: OLD})
        for bad in (Transfer("x", 1, 64), Transfer("x", 0, 0), Transfer("x", 0, 64, write=True)):
            with self.subTest(offer=bad):
                with self.assertRaisesRegex(ValueError, "invalid DMA burst"):
                    port.step(0, offer=bad)
        port.step(0, offer=Transfer("x", 0, 64))
        with self.assertRaisesRegex(ValueError, "reused DMA tag"):
            port.step(1, offer=Transfer("x", 0, 64))

    def test_backend_cannot_complete_unknown_or_duplicate_identity(self):
        class CorruptBackend(TimedBackend):
            def __init__(self, duplicate):
                super().__init__(depth=1, latency=2)
                self.duplicate = duplicate

            def completions(self, cycle):
                identifiers = super().completions(cycle)
                if not identifiers:
                    return identifiers
                return identifiers * 2 if self.duplicate else [("different", 0)]

        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                port = DmaPort(CorruptBackend(duplicate), queue_depth=1, credits=1,
                               response_depth=1, initial_memory={0: OLD})
                port.step(0, offer=Transfer("live", 0, 64))
                port.step(1)
                port.step(2)
                with self.assertRaisesRegex(ValueError, "unknown or duplicate backend completion identity"):
                    port.step(3)
                self.assertFalse(events(port, "read_return", "live"))
