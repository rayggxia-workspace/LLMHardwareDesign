"""Small independent physical beat/RMW and typed micro fee controls."""
import copy
import unittest

from calendar76 import Calendar, invariant_packets, packets_with_rmw, partial_edges, serial_certificate


class CalendarPrimitiveTests(unittest.TestCase):
    def test_partial_line_rmw_and_full_packet_fifo(self):
        self.assertEqual([partial_edges(0, 16), partial_edges(4, 4), partial_edges(4, 16)], [0, 1, 2])
        cost, peak = packets_with_rmw(0, 1, 1984)
        self.assertEqual((cost["src_beats"], cost["dst_beats"], cost["dst_rmw_beats"], peak), (124, 125, 2, 2048))
        cost, peak = packets_with_rmw(0, 0, 8192)
        self.assertEqual((cost["packets"], cost["wire_bytes"], cost["dst_rmw_beats"], peak), (5, 8352, 0, 2016))

    def test_affine_word_access_may_change_offset_without_changing_fee(self):
        cost, peak = invariant_packets(0, 0, 4, [], [4], [8])
        self.assertEqual((cost["dst_rmw_beats"], peak), (1, 64))
        with self.assertRaisesRegex(ValueError, "invariant affine"):
            invariant_packets(0, 0, 16, [], [1], [2])

    def test_micro_rmw_width_fee_is_independently_reconstructed(self):
        audit = Calendar.__new__(Calendar)
        audit.cal = {"source": {"micro_sha256": "1"*64}, "ops": {"add_s64": {"proof": {}, "costs": {
            "scalar_ALU_dependency_cycles": 1, "software_controller_dispatches": 1, "byte_store_reads": 1,
            "result_read_bytes": 1, "byte_store_writes": 1, "input_load_bytes": 1,
            "SIMD8_qualified": False, "frame_capacity_bytes": 512, "scratch_peak_bytes": 1}}}}
        audit.macros = [{"meta": {"token": 0, "phase": p}} for p in ("front", "down", "norm")]
        audit.phases = {(0, i): (i, i+1) for i in range(3)}
        audit.objects = {"V.microframe": {"object": "V.microframe", "bank": "V", "offset": 0, "bytes": 512,
                                         "lifetime": ["task_start", "task_end"]}}
        audit.peak_fifo = 0
        counts = {"op.add_s64": 1, "micro_alu_cycles": 1, "micro_dispatch_cycles": 1,
                  "micro_frame_read_bytes": 2, "micro_frame_write_bytes": 2, "bank_beats": 6,
                  "micro_frame_write_RMW_read_beats": 2, "wire_bytes": 192, "wire_beats": 12, "packets": 4, "payload_bytes": 4}
        node = {"kind": "micro", "start": 0, "end": 20, "op": "add_s64", "count": 1,
                "microprogram_sha256": "1"*64, "proof": {}, "scratch_peak_bytes": 1,
                "resources": [{"name": name, "start": 0, "end": 20} for name in ("VR8", "bank.V", "BUS")],
                "counts": counts, "FIFO_peak_bytes": 1024, "operand_register_bytes": 5, "caller_staging_budget_bytes": 512,
                "retiming_certificate": {"kind": "fixed_source_byte_microprogram", "all_accesses_within_allocated_frame": True,
                    "input_initialization_and_result_extract_included": True, "duration_formula": "ALU+dispatch+4*frame_reads+5*frame_writes"},
                "accesses": [{"object": "V.microframe", "offset": 0, "bytes": 1, "mode": mode, "repeat": 1,
                              "stride": 0, "index_strides": [], "address_class": {"kind": "source_bound_microprogram_byte_frame",
                                  "minimum": 0, "maximum": 511, "access_count": 2}} for mode in ("read", "write")]}
        self.assertEqual(audit.leaf(node, [], 0), counts)
        bad = copy.deepcopy(node); bad["counts"]["bank_beats"] = 4
        with self.assertRaisesRegex(ValueError, "independently derived"):
            audit.leaf(bad, [], 0)

    def test_eight_kib_copy_needs_packet_retiming_not_aggregate_fifo(self):
        audit = Calendar.__new__(Calendar)
        audit.macros = [{"meta": {"token": 0, "phase": p}} for p in ("front", "down", "norm")]
        audit.phases = {(0, i): (i, i+1) for i in range(3)}; audit.peak_fifo = 0
        audit.objects = {name: {"object": name, "bank": bank, "offset": 0, "bytes": 8192,
                               "lifetime": ["task_start", "task_end"]} for name, bank in (("source", "EXT"), ("destination", "M"))}
        counts, peak = packets_with_rmw(0, 0, 8192); counts["bank_beats"] = 1024
        node = {"kind": "transfer", "start": 0, "end": 1546,
                "resources": [{"name": name, "start": 0, "end": 1546} for name in ("bank.EXT", "BUS", "bank.M")],
                "counts": counts, "FIFO_peak_bytes": peak,
                "packet": {"src": "source", "dst": "destination", "src_offset": 0, "dst_offset": 0,
                           "bytes": 8192, "partial_write": "endpoint RMW"},
                "accesses": [{"object": name, "offset": 0, "bytes": 8192, "mode": mode,
                              "repeat": 1, "stride": 0, "index_strides": []} for name, mode in (("source", "read"), ("destination", "write"))],
                "serial_packet_retiming_certificate": serial_certificate(0, 0, audit.objects["source"], audit.objects["destination"], 8192, 0, 0, [], [])}
        self.assertEqual(audit.leaf(node, [], 0), counts)
        old = copy.deepcopy(node); del old["serial_packet_retiming_certificate"]
        old["resources"] = [{"name": "bank.EXT", "start": 0, "end": 512},
                            {"name": "BUS", "start": 512, "end": 1034}, {"name": "bank.M", "start": 1034, "end": 1546}]
        with self.assertRaisesRegex(ValueError, "explicit bounded serial"):
            audit.leaf(old, [], 0)
        alias = copy.deepcopy(node); audit.objects["destination"]["bank"] = "EXT"
        alias["serial_packet_retiming_certificate"] = serial_certificate(0, 0, audit.objects["source"], audit.objects["destination"], 8192, 0, 0, [], [])
        with self.assertRaisesRegex(ValueError, "alias across affine"):
            audit.leaf(alias, [], 0)


if __name__ == "__main__": unittest.main()
