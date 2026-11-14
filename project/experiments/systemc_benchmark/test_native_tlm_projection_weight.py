import unittest
from collections import Counter
from types import SimpleNamespace

from native_tlm_projection import Projection
from native_tlm_timing import Clock


class DelayedReads:
    def __init__(self, clock, delay):
        self.clock = clock
        self.delay = delay
        self.issues = []
        self.callbacks = []

    def submit(self, transfer, done, *, channel):
        address = transfer.address
        self.issues.append((self.clock.now, address, channel))

        def returned():
            self.callbacks.append(address)
            done()

        self.clock.after(self.delay(address), returned)


class ProjectionWeightTest(unittest.TestCase):
    def test_round_robin_credit_and_record_order(self):
        clock = Clock()
        # Delay the first lane head and reorder raw DRAM callbacks.
        dram = DelayedReads(clock, lambda address: 900 if address == 0x7c0 else 400)
        sources = SimpleNamespace(core_ps=10)
        memory = lambda address: address.to_bytes(8, "little") * 8
        p = Projection(clock, dram, memory, sources, sources, source_word=0,
                       scratch_word=512, rtl_weight_fetch=True)
        complete = {}
        records = [(0x7c0, 1088), (0x2000, 1088), (0x4800, 1152), (0x6000, 1088)]
        for base, size in records:
            def ready(data, release, base=base):
                complete[base] = clock.now, data
                release()
            p.weight_fetch.enqueue(base, size, ready)

        clock.until(lambda: len(complete) == len(records))
        self.assertEqual(p.stats["weight_peak_outstanding"], 32)
        self.assertEqual(p.stats["weight_read_issues"], 69)
        self.assertEqual(p.stats["weight_read_returns"], 69)
        self.assertEqual(dram.callbacks[0], 0x800)
        self.assertEqual(dram.issues[0], (80, 0x7c0, 0))
        self.assertTrue(all(count == 1 for count in Counter(t for t, _, _ in dram.issues).values()))
        issued = {(address, channel) for _, address, channel in dram.issues}
        for base, size in records:
            self.assertEqual(complete[base][1], b"".join(
                memory(base + offset) for offset in range(0, size, 64)))
            self.assertTrue(all((base + offset, base >> 11 & 1) in issued
                                for offset in range(0, size, 64)))
        self.assertLess(dram.issues.index(next(x for x in dram.issues if x[1] == 0x2000)),
                        dram.issues.index(next(x for x in dram.issues if x[1] == 0xbc0)))
        self.assertFalse(p.weight_fetch.banks)
        self.assertEqual(p.weight_fetch.outstanding, 0)


if __name__ == "__main__":
    unittest.main()
