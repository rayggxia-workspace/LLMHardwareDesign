"""Small synthetic lifetime/capacity and true physical-access boundary tests."""
import unittest

from physical76 import (CAPACITIES, check_access, check_regions, local_beats,
                        packet_segments, phase_intervals)


def region(name, size, time=None):
    return {"object": name, "bank": "V", "offset": 0, "bytes": size,
            "lifetime": ["task_start", "task_end"] if time is None else time}


class FiniteStorageTests(unittest.TestCase):
    def test_actual_eight_full_returns_rejected_in_v(self):
        self.assertEqual(8*1536*4, 49152)
        with self.assertRaisesRegex(ValueError, "finite capacity"):
            check_regions(CAPACITIES, [region("eight_returns", 49152)], 10)

    def test_reuse_only_after_last_consumer(self):
        objects, high = check_regions(CAPACITIES, [region("gateup", 4096, [0, 5]),
                                                   region("norm", 4096, [5, 10])], 10)
        self.assertEqual(high, {"V": 4096})
        a = {"object": "gateup", "offset": 0, "bytes": 64, "mode": "read",
             "repeat": 1, "stride": 0, "index_strides": []}
        check_access(a, objects, (), 4, 10)
        with self.assertRaisesRegex(ValueError, "live interval"):
            check_access(a, objects, (), 5, 10)
        with self.assertRaisesRegex(ValueError, "live alias"):
            check_regions(CAPACITIES, [region("gateup", 4096, [0, 6]), region("norm", 4096, [5, 10])], 10)

    def test_full_affine_extent_not_just_first_tile(self):
        objects, _ = check_regions(CAPACITIES, [region("mid", 4096)], 10)
        a = {"object": "mid", "offset": 0, "bytes": 512, "mode": "read",
             "repeat": 1, "stride": 0, "index_strides": [512]}
        check_access(a, objects, (8,), 1, 10)
        with self.assertRaisesRegex(ValueError, "affine access"):
            check_access(a, objects, (9,), 1, 10)

    def test_actual_weight_gather_beats(self):
        access = {"offset": 0, "bytes": 1, "repeat": 16, "stride": 512, "index_strides": [1]}
        self.assertEqual(local_beats(0, access, (512,)), 16)
        packed = packet_segments(15, 0, 512, 16, 512, 512)
        self.assertEqual(packed["src_beats"], 16*33)
        self.assertEqual(packed["dst_beats"], 16*32)
        self.assertEqual(packed["wire_bytes"], 16*544)

    def test_different_leading_beat_classes_must_not_reuse_one_count(self):
        access = {"offset": 0, "bytes": 16, "repeat": 1, "stride": 0, "index_strides": [1]}
        with self.assertRaisesRegex(ValueError, "noninvariant"):
            local_beats(0, access, (2,))

    def test_full_merge_can_reuse_dead_front_storage(self):
        macros = [{"meta": {"token": t, "phase": p}} for t in range(2) for p in ("front", "down", "norm")]
        def phased(name, count, phase, offset=1408):
            obj = region(name, count)
            obj.update(offset=offset, lifetime={"kind": "token_phase", "phases": [phase], "every_token": True,
                                              "barriers": "front -> down -> norm -> next_token"})
            return obj
        allocations = [region("global", 1408), phased("front", 9728, "front"),
                       phased("fullH_s64", 12288, "down"), phased("O16_RQ", 480, "down", 13696)]
        objects, high = check_regions(CAPACITIES, allocations, len(macros), macros)
        self.assertEqual(high["V"], 14176)
        access = {"object": "front", "offset": 0, "bytes": 16, "mode": "read", "repeat": 1,
                  "stride": 0, "index_strides": []}
        with self.assertRaisesRegex(ValueError, "live interval"):
            check_access(access, objects, (), 1, len(macros), phase_intervals(macros))
        bad = macros.copy(); bad[1] = {"meta": {"token": 0, "phase": "norm"}}
        with self.assertRaisesRegex(ValueError, "phase barrier"):
            check_regions(CAPACITIES, allocations, len(bad), bad)


if __name__ == "__main__":
    unittest.main()
