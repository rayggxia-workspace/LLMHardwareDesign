import copy
import json
import pathlib
import unittest
import oracle

CASES = oracle.cases()
TRACES = {t["name"]: t for t in oracle.golden_traces()}


def trace(name="receiver_first_16B"):
    return copy.deepcopy(TRACES[name])


def at(value, name):
    return next(e for e in value["events"] if e["name"] == name)


def remove(value, name):
    value["events"] = [e for e in value["events"] if e["name"] != name]


def byte(hex_text, offset, value):
    b = bytearray.fromhex(hex_text)
    b[offset] = value
    return bytes(b).hex()


class ReferenceTests(unittest.TestCase):
    def reject(self, value, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            oracle.check_trace(CASES[value["case"]], value)

    def test_four_authored_reference_traces(self):
        for t in TRACES.values():
            result = oracle.check_trace(CASES[t["case"]], t)
            self.assertTrue(result["reference_trace_valid"])
            self.assertFalse(result["instructions_executed"])
            self.assertFalse(result["rtl_tested"])

    def test_encoding_has_independent_empty_words(self):
        encoded = oracle.encode_cases()
        empty = encoded["cases"][0]
        self.assertEqual(empty["programs"]["local0"], ["0000000000000000000000000000004f"])
        self.assertEqual(empty["programs"]["mother"][0], "00000000000000000000000000000010")
        self.assertEqual(empty["programs"]["mother"][1], "00000000010000000000000000000011")
        self.assertFalse(empty["complete_image"])
        self.assertFalse(empty["execution_tested"])

    def test_receiver_task_does_not_claim_output_object(self):
        encoded = oracle.encode_cases()["cases"][2]["records"]
        rx = oracle.codec.unpack_record("task", bytes.fromhex(encoded["1"]["task"][0]))
        tx = oracle.codec.unpack_record("task", bytes.fromhex(encoded["0"]["task"][0]))
        self.assertEqual(rx["output_object_mask"], 0)
        self.assertEqual(tx["output_object_mask"], 1)
        self.assertEqual(rx["retained_object_mask"], 0)

    def test_native_payload_is_held_under_backpressure(self):
        t = trace("single_M_clear")
        at(t, "native_cmd")["payload"]["cmd_index"] = 1
        self.reject(t, "backpressure")
        t = trace("single_M_clear")
        at(t, "native_rsp")["event"]["task_sequence"] = 2
        self.reject(t, "backpressure")

    def test_held_valid_cannot_be_dropped(self):
        t = trace("single_M_clear")
        at(t, "native_rsp")["valid"] = False
        self.reject(t, "backpressure")

    def test_CALL_needs_reserved_terminal_credit(self):
        t = trace("empty_task")
        remove(t, "reserve_0")
        self.reject(t, "CALL without credit")

    def test_producer_CALL_cannot_skip_READY_consumption(self):
        t = trace()
        remove(t, "consume_ready")
        self.reject(t, "before READY")

    def test_READY_requires_armed_receiver(self):
        t = trace()
        remove(t, "arm_destination")
        self.reject(t, "local event order|READY before RX")

    def test_native_response_requires_accepted_command(self):
        t = trace("single_M_clear")
        remove(t, "native_cmd_held")
        remove(t, "native_cmd")
        self.reject(t, "response without command")

    def test_WAIT_is_not_command_acceptance(self):
        t = trace("single_M_clear")
        remove(t, "native_rsp_held")
        remove(t, "native_rsp")
        self.reject(t, "WAIT before completion")

    def test_store_ack_needs_actual_data_observation(self):
        t = trace()
        remove(t, "cross_data_held")
        remove(t, "cross_data")
        self.reject(t, "store ACK before DATA")

    def test_ACK_generation_needs_store_ack(self):
        t = trace()
        remove(t, "destination_store_ack")
        self.reject(t, "ACK before store")

    def test_TX_cannot_finish_before_remote_ACK_received(self):
        t = trace()
        remove(t, "cross_ack_recv")
        self.reject(t, "service completed before actual ACK")

    def test_local_WAIT_cannot_move_before_completion(self):
        t = trace()
        # Keep local program-side event order but force premature completion fact.
        source = at(t, "source_complete")
        i = t["events"].index(source)
        t["events"].insert(i, t["events"].pop(next(j for j,e in enumerate(t["events"])
                                                   if e["name"] == "wait_source")))
        self.reject(t, "WAIT before completion")

    def test_DROP_cannot_discard_a_second_unretired_borrow(self):
        t = trace()
        c = copy.deepcopy(CASES[t["case"]])
        c["pairs"]["late"] = dict(src=255, dst=0, edge=13)
        c["operations"]["borrow"] = dict(kind="rx", task="0", token=1,
            service_sequence=2, descriptor=2, object=0, pair="late")
        c["tasks"]["0"]["expected_local_events"].insert(-2, "arm_rx")
        event = copy.deepcopy(at(t, "arm_input"))
        event["name"] = "late_borrow"
        event["event"]["operation"] = "borrow"
        event["event"]["service_sequence"] = 2
        t["events"].insert(t["events"].index(at(t, "drop_source")), event)
        with self.assertRaisesRegex(ValueError, "DROP with outstanding"):
            oracle.check_trace(c, t)

    def test_terminal_cannot_hide_unconsumed_local_token(self):
        t = trace("single_M_clear")
        c = copy.deepcopy(CASES[t["case"]])
        remove(t, "wait_clear")
        c["tasks"]["0"]["expected_local_events"].remove("wait")
        with self.assertRaisesRegex(ValueError, "terminal with live obligations"):
            oracle.check_trace(c, t)

    def test_duplicate_remote_ACK_reject(self):
        t = trace()
        i = t["events"].index(at(t, "source_complete"))
        t["events"].insert(i, copy.deepcopy(at(t, "cross_ack_recv")))
        self.reject(t, "unmatched/duplicate ACK")

    def test_wrong_ACK_identity_and_byte_count_reject(self):
        for offset, value in [(4, 8), (8, 2), (12, 13), (32, 2), (40, 15)]:
            t = trace()
            e = at(t, "cross_ack_recv")
            e["payload"]["header_hex"] = byte(e["payload"]["header_hex"], offset, value)
            self.reject(t, "identity or byte count")

    def test_stale_task_tag_reject(self):
        t = trace("empty_task")
        at(t, "consume_0")["event"]["epoch"] = 0
        self.reject(t, "stale job/epoch")

    def test_service_sequence_cannot_be_reused_with_recycled_token(self):
        t = trace()
        c = copy.deepcopy(CASES[t["case"]])
        c["operations"]["source_tx"]["service_sequence"] = 0
        for e in t["events"]:
            if e["event"].get("operation") == "source_tx":
                e["event"]["service_sequence"] = 0
        with self.assertRaisesRegex(ValueError, "sequence reused"):
            oracle.check_trace(c, t)

    def test_response_cannot_be_observed_on_wrong_channel(self):
        t = trace("single_M_clear")
        for e in t["events"]:
            if e["event"]["kind"] == "native_rsp":
                e["channel"] = "M.command"
        self.reject(t, "wrong transport channel")

    def test_duplicate_response_and_global_consume_reject(self):
        t = trace("single_M_clear")
        e = copy.deepcopy(at(t, "native_rsp"))
        t["events"].insert(t["events"].index(at(t, "wait_clear")), e)
        self.reject(t, "response without command/duplicate")
        t = trace("empty_task")
        i = t["events"].index(at(t, "global_end"))
        t["events"].insert(i, copy.deepcopy(at(t, "consume_0")))
        self.reject(t, "global completion absent/duplicate")

    def test_peer_error_must_not_be_reported_as_success(self):
        t = trace("single_M_clear_peer_error")
        for e in t["events"]:
            if e["event"]["kind"] == "terminal":
                e["payload"]["hex"] = byte(e["payload"]["hex"], 2, 2)
        self.reject(t, "terminal tuple/status mismatch")
        t = trace("single_M_clear_peer_error")
        at(t, "global_error")["event"]["kind"] = "global_end"
        self.reject(t, "global success hides error")

    def test_packet_payload_cannot_change_between_source_and_destination(self):
        t = trace()
        for name in ["cross_data_held", "cross_data"]:
            at(t, name)["payload"]["data_hex"] = "ff" * 16
        self.reject(t, "source payload changed")

    def test_state_record_cannot_fake_wire_handshake(self):
        t = trace("empty_task")
        remove(t, "call_0_held")
        at(t, "call_0")["kind"] = "state"
        self.reject(t, "requires handshake")

    def test_global_END_requires_both_task_results(self):
        t = trace()
        remove(t, "consume_0")
        self.reject(t, "global terminal before all obligations")

    def test_stall_duration_is_not_a_fixed_latency_claim(self):
        t = trace("single_M_clear")
        held = copy.deepcopy(at(t, "native_rsp_held"))
        i = t["events"].index(at(t, "native_rsp"))
        t["events"][i:i] = [copy.deepcopy(held) for _ in range(31)]
        self.assertTrue(oracle.check_trace(CASES[t["case"]], t)["reference_trace_valid"])


if __name__ == "__main__":
    unittest.main()
