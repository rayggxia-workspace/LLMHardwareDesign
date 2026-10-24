import copy
import unittest

import receive_service as receiver


def inventory():
    caps = {"V": 16384, "R": 32768, "M": 32768, "EXT": 134217728, "ROM": 4260100,
            **{f"S{i}": 32768 for i in range(8)}}
    return {"capacities": caps, "ports": {k: {"kind": "1RW", "bits": 128} for k in caps},
            "lanes": {"resource": "VR8", "S8_lanes": 8},
            "matrix": {"resource": "M256", "S8_PEs": 256, "shape": [16, 16], "effective_PEs_single_row": 16},
            "byte_cost": receiver.BYTE_COST.copy(), "alu_slots64": 10, "alu_slots128": 18,
            "SFUiterations": {"division128": 128, "isqrt128": 64}, "wide_factor": 1,
            "packet": {"header_bytes": 32, "beat_bytes": 16, "max_payload": 1984,
                       "FIFO_bytes": 2048, "BUS_count": 1, "BUS_bits": 128}}


def allocation(name, bank, off=0, n=4096):
    return {"object": name, "bank": bank, "offset": off, "bytes": n,
            "lifetime": ["task_start", "task_end"]}


class CalendarTests(unittest.TestCase):
    def test_modulo_sixteen_scalar_loop_address_classes(self):
        self.assertEqual(receiver.loop_residues(0, [4], (128,)), {0, 4, 8, 12})
        self.assertEqual(receiver.loop_residues(0, [8], (64,)), {0, 8})
        self.assertEqual(receiver.loop_residues(3, [16, 32], (32, 32)), {3})
        self.assertEqual(receiver.loop_residues(2, [4], (2,)), {2, 6})

    def test_physical_packet_leading_beat_each_segment(self):
        count = receiver.packet_accounting(1, 15, 1985)
        self.assertEqual(count, {"payload_bytes": 1985, "src_beats": 126, "dst_beats": 126,
                                 "wire_beats": 129, "wire_bytes": 2064, "packets": 2})

    def test_same_inventory_and_no_overlap(self):
        inv = inventory()
        objects, water = receiver.check_allocations(inv, [allocation("a", "V"), allocation("b", "V", 4096)])
        self.assertEqual(water["V"], 8192)
        with self.assertRaisesRegex(ValueError, "overlap"):
            receiver.check_allocations(inv, [allocation("a", "V"), allocation("b", "V", 4095)])
        inv["ports"]["V"]["kind"] = "2RW"
        with self.assertRaisesRegex(ValueError, "one true"):
            receiver.check_allocations(inv, [allocation("a", "V")])

    def test_finite_loop_arithmetic_and_resource_tamper(self):
        inv = inventory()
        leaf = {"kind": "compute", "start": 0, "end": 67, "counts": {"mul32": 2},
                "matrix_active_PEs": 16, "resources": [{"name": "VR8", "start": 0, "end": 67}]}
        node = {"kind": "loop", "start": 0, "end": 201, "period": 67, "count": 3, "body": [leaf]}
        result = receiver.verify_tree([node], 201, {}, inv)
        self.assertEqual(result["mul32"], 6)
        self.assertEqual(result["expanded_leaves"], 3)
        bad = copy.deepcopy(node)
        bad["body"][0]["resources"][0]["end"] -= 1
        with self.assertRaisesRegex(ValueError, "resource durations"):
            receiver.verify_tree([bad], 201, {}, inv)

    def test_affine_suffix_addresses_and_capacity(self):
        objects = {"a": allocation("a", "V", n=1024)}
        access = {"object": "a", "offset": 0, "bytes": 4, "repeat": 1, "stride": 0, "index_strides": [4]}
        receiver.address_range(access, objects, (8, 256))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            receiver.address_range(access, objects, (8, 257))

    def test_transfer_fifo_must_include_physical_pad(self):
        inv = inventory()
        objects = {"source": allocation("source", "EXT"), "dest": allocation("dest", "R")}
        counts = receiver.packet_accounting(0, 0, 2)
        event = {"kind": "transfer", "start": 0, "end": 5,
                 "resources": [{"name": "bank.EXT", "start": 0, "end": 1},
                               {"name": "BUS", "start": 1, "end": 4},
                               {"name": "bank.R", "start": 4, "end": 5}],
                 "counts": counts, "FIFO_peak_bytes": 48,
                 "accesses": [{"object": name, "offset": 0, "bytes": 2, "repeat": 1,
                               "stride": 0, "index_strides": [], "mode": mode}
                              for name, mode in (("source", "read"), ("dest", "write"))],
                 "packet": {"src": "source", "dst": "dest", "src_offset": 0, "dst_offset": 0,
                            "bytes": 2, "segments": 1, "src_stride": 0, "dst_stride": 0}}
        receiver.verify_tree([event], 5, objects, inv)
        event["FIFO_peak_bytes"] = 34
        with self.assertRaisesRegex(ValueError, "FIFO"):
            receiver.verify_tree([event], 5, objects, inv)


if __name__ == "__main__":
    unittest.main()
