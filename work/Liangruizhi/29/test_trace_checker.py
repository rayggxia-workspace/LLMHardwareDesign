import copy
import unittest

from trace_checker import Checker


ZERO = "0" * 128
FULL = "f" * 16
PATTERN = "aa" * 64


def request(write=False, tag=0, bank=0, addr=0, data=ZERO, strobe=FULL, ready=True):
    return dict(valid=True, ready=ready, bank=bank, write=write, addr=addr, tag=tag,
                wdata_hex=data, wstrb_hex=strobe)


def response(write=False, tag=0, data=ZERO, ready=True):
    return dict(valid=True, ready=ready, write=write, tag=tag, data_hex=data)


def idle():
    return dict(valid=False, ready=True)


def cycle(n, req=None, rsp=None, reset=False):
    return dict(cycle=n, reset=reset, req=req or [idle() for _ in range(3)], rsp=rsp or [idle() for _ in range(3)])


def fixture():
    rows = [cycle(0, [request(True, 10, data=PATTERN), idle(), idle()]),
            cycle(1, [request(False, 11), idle(), idle()], [response(True, 10), idle(), idle()]),
            cycle(2, [request(False, 12), idle(), idle()], [response(False, 11, PATTERN), idle(), idle()]),
            cycle(3, rsp=[response(False, 12, PATTERN, False), idle(), idle()]),
            cycle(4, rsp=[response(False, 12, PATTERN, False), idle(), idle()]),
            cycle(5, rsp=[response(False, 12, PATTERN), idle(), idle()]), cycle(6)]
    return rows


def run(rows, mode=0, depth=1, mask=63, strict=True):
    checker = Checker(dict(type="config", mode=mode, depth=depth, mask=mask), strict)
    for row in rows:
        checker.process(row)
    return checker.finish()


class TraceCheckerTests(unittest.TestCase):
    def test_depth1_full_pop_push_and_stalled_read(self):
        result = run(fixture())
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["counts"]["requests_accepted"], 3)
        self.assertEqual(result["counts"]["read_bytes_unknown"], 0)
        self.assertEqual(result["response_queue_peak"], [1, 0, 0])

    def test_independent_mutations_detected(self):
        mutations = []
        wrong = copy.deepcopy(fixture()); wrong[2]["rsp"][0]["data_hex"] = ZERO
        mutations.append((wrong, "read_data"))
        wrong = copy.deepcopy(fixture()); wrong[4]["rsp"][0]["tag"] = 99
        mutations.append((wrong, "response_changed_while_stalled"))
        wrong = copy.deepcopy(fixture()); wrong[0]["rsp"][0] = response(True, 10)
        mutations.append((wrong, "response_valid_or_latency"))
        wrong = copy.deepcopy(fixture()); wrong[4]["req"][0] = request(False, 13)
        mutations.append((wrong, "response_credit_overflow"))
        wrong = copy.deepcopy(fixture()); wrong[2]["req"][0] = request(True, 12)
        mutations.append((wrong, "half_duplex_write_during_read_response"))
        for rows, code in mutations:
            with self.subTest(code=code):
                result = run(rows)
                self.assertEqual(result["status"], "FAIL")
                self.assertIn(code, [e["code"] for e in result["errors"]])

    def test_stalled_request_cannot_change_or_disappear(self):
        for replacement in (idle(), request(False, 2, ready=False)):
            rows = [cycle(0, [request(False, 1, ready=False), idle(), idle()]),
                    cycle(1, [replacement, idle(), idle()])]
            result = run(rows, strict=False)
            self.assertIn("request_changed_while_stalled", [e["code"] for e in result["errors"]])

    def test_port_mask_same_row_guards(self):
        configs = [(0, 63, [request(True, 1), request(True, 2, addr=1), idle()], "bank_port_contract"),
                   (1, 63, [request(True, 1), request(True, 2, addr=1), idle()], "bank_port_contract"),
                   (2, 63, [request(False, 1), request(False, 2), idle()], "same_row_double_grant"),
                   (0, 62, [request(True, 1), idle(), idle()], "disabled_link_accepted")]
        for mode, mask, req, code in configs:
            result = run([cycle(0, req)], mode=mode, mask=mask, strict=False)
            self.assertIn(code, [e["code"] for e in result["errors"]])

    def test_partial_strobe_preserves_unwritten_bytes_and_zero_is_noop(self):
        changed = "aa" * 63 + "12"
        rows = [cycle(0, [request(True, 1, data=PATTERN), idle(), idle()]),
                cycle(1, [request(True, 2, data="12", strobe="1"), idle(), idle()], [response(True, 1), idle(), idle()]),
                cycle(2, [request(True, 3, data=ZERO, strobe="0"), idle(), idle()], [response(True, 2), idle(), idle()]),
                cycle(3, [request(False, 4), idle(), idle()], [response(True, 3), idle(), idle()]),
                cycle(4, rsp=[response(False, 4, changed), idle(), idle()]), cycle(5)]
        result = run(rows)
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["counts"]["write_bytes_committed"], 65)
        self.assertEqual(result["counts"]["zero_strobe_writes"], 1)

    def test_reset_clears_control_but_preserves_memory(self):
        rows = [cycle(0, [request(True, 1, data=PATTERN), idle(), idle()]), cycle(1, reset=True),
                cycle(2, [request(False, 2), idle(), idle()]),
                cycle(3, rsp=[response(False, 2, PATTERN), idle(), idle()]), cycle(4)]
        result = run(rows)
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["counts"]["responses_cancelled_by_reset"], 1)

    def test_unknown_bytes_are_reported_and_can_be_forbidden(self):
        rows = [cycle(0, [request(False, 1), idle(), idle()]), cycle(1, rsp=[response(False, 1), idle(), idle()]), cycle(2)]
        self.assertEqual(run(rows, strict=False)["counts"]["read_bytes_unknown"], 64)
        self.assertEqual(run(rows, strict=False)["status"], "PASS")
        self.assertEqual(run(rows, strict=True)["status"], "FAIL")

    def test_semantic_generation_even_if_data_aliases_and_partial_known_bytes(self):
        write = request(True, 1, data=PATTERN, strobe="f")
        write.update(generation=257, generation_offset=0)
        read = request(False, 2, strobe="f")
        read.update(generation=257, generation_offset=0)
        rows = [cycle(0, [write, idle(), idle()]),
                cycle(1, [read, idle(), idle()], [response(True, 1), idle(), idle()]),
                cycle(2, rsp=[response(False, 2, PATTERN), idle(), idle()]), cycle(3)]
        result = run(rows, strict=False)
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["counts"]["versioned_read_bytes"], 4)
        # An 8-bit test-data encoding might alias generation 1 and 257; integer
        # byte-origin tracking detects the wrong version without copying it.
        bad = copy.deepcopy(rows)
        bad[1]["req"][0]["generation"] = 1
        result = run(bad, strict=False)
        self.assertIn("graph_read_generation_or_offset", [e["code"] for e in result["errors"]])

    def test_combined_external_data_gap_is_optional_program_contract(self):
        checker = Checker(dict(type="config", mode=0, depth=2, mask=63), False, 2)
        checker.process(cycle(0, [idle(), idle(), request(True, 1)]))
        checker.process(cycle(1, [idle(), idle(), request(True, 2)], [idle(), idle(), response(True, 1)]))
        checker.process(cycle(2, rsp=[idle(), idle(), response(True, 2)]))
        checker.process(cycle(3))
        result = checker.finish()
        self.assertIn("external_data_service_gap", [e["code"] for e in result["errors"]])


if __name__ == "__main__":
    unittest.main()
