import copy
import json
import unittest
import check_cycles as check
import examples
import generate

EXAMPLES = examples.build()


def trace(name="M_clear_backpressure"):
    return copy.deepcopy(next(t for t in EXAMPLES["traces"] if t["name"] == name))


def find(t,predicate):
    return next(row["signals"] for row in t["cycles"] if predicate(row["signals"]))


class BoundaryTests(unittest.TestCase):
    def reject(self,t,pattern=".",complete=True):
        with self.assertRaisesRegex(ValueError,pattern):
            check.check_trace(t,complete)

    def test_declarations_and_inventory_rebuild(self):
        for name,text in generate.artifacts().items():
            self.assertEqual((generate.HERE/name).read_bytes(),text.encode("utf-8"))
        pins = [p for g in generate.contract()["groups"] for p in g["pins"]]
        self.assertEqual(len(pins),92)
        self.assertEqual(len(set(p["name"] for p in pins)),92)
        self.assertEqual(sum(generate.contract()["payload_register_budget_bytes"].values()),688)

    def test_four_authored_examples_and_flits_are_explicitly_not_RTL(self):
        saved = json.loads((generate.HERE/"timing_examples.json").read_bytes().decode("utf-8"))
        self.assertEqual(saved,EXAMPLES)
        self.assertFalse(saved["rtl_tested"])
        for t in saved["traces"]:
            result = check.check_trace(t)
            self.assertTrue(result["boundary_valid"])
            self.assertFalse(result["rtl_tested"])
            self.assertEqual(result["evidence"],"authored_expected")
        f = saved["flit_example"]
        check.check_flits(bytes.fromhex(f["packet_hex"]),f["cycles"])

    def test_BEGIN_wins_over_simultaneous_new_CALL(self):
        t = trace("prepare_then_deploy")
        row = find(t,lambda s:s.get("cfg_req_valid_i") and s["cfg_req_op_i"] == 0)
        row.update(task_valid_i=1,task_ready_o=1)
        self.reject(t,"BEGIN priority")

    def test_local_reset_does_not_allow_image_or_task_admission(self):
        t = trace()
        t["cycles"][0]["signals"]["image_valid_o"] = 1
        self.reject(t,"reset valid")

    def test_pin_width_and_unknown_names_reject(self):
        for key,value in [("pm_req_address_o",16384),("invented_signal",1)]:
            t = trace()
            t["cycles"][0]["signals"][key] = value
            self.reject(t,"width|unknown")

    def test_service_request_snapshot_is_held_during_stall(self):
        t = trace()
        row = find(t,lambda s:s.get("svc_req_valid_o") and s.get("svc_req_ready_i") == 0)
        row["svc_req_descriptor_o"] = hex(check.number(row["svc_req_descriptor_o"]) ^ 1)
        self.reject(t,"held tuple")

    def test_service_response_identity_is_held_during_stall(self):
        t = trace()
        row = find(t,lambda s:s.get("svc_rsp_valid_i") and s.get("svc_rsp_ready_o") == 0)
        row["svc_rsp_task_sequence_i"] = 2
        self.reject(t,"held tuple")

    def test_return_packet_cannot_change_under_stall(self):
        t = trace()
        row = find(t,lambda s:s.get("event_valid_o") and s.get("event_ready_i") == 0)
        row["event_packet_o"] = hex(check.number(row["event_packet_o"]) ^ 1)
        self.reject(t,"held tuple")

    def test_cfg_success_cannot_precede_actual_storage_ACK(self):
        t = trace()
        row = find(t,lambda s:s.get("pm_req_valid_o") and s.get("pm_req_write_o"))
        row.update(cfg_rsp_valid_o=1,cfg_rsp_ready_i=1,cfg_rsp_generation_o=1)
        self.reject(t,"before stored ACK")

    def test_verify_needs_all_write_ACKs_and_full_readback(self):
        t = trace()
        row = find(t,lambda s:s.get("cfg_req_valid_i") and s["cfg_req_op_i"] == 1)
        row.update(cfg_req_op_i=3,cfg_req_proof_i=1)
        self.reject(t,"verification before")

    def test_local_PREPARE_does_not_admit_without_cohort_deploy(self):
        t = trace("prepare_then_deploy")
        row = find(t,lambda s:s["life_o"] == check.LIFE["PREPARED"] and not s["deploy_valid_i"])
        row["image_valid_o"] = 1
        self.reject(t,"cohort/image")

    def test_runtime_configuration_ready_must_be_low(self):
        t = trace()
        row = find(t,lambda s:s["life_o"] == check.LIFE["RUNNING"])
        row["cfg_req_ready_o"] = 1
        self.reject(t,"running/config")

    def test_program_write_is_forbidden_in_runtime(self):
        t = trace()
        row = find(t,lambda s:s.get("pm_req_valid_o") and s.get("trace_pm_owner_o") == 1)
        row["pm_req_write_o"] = 1
        self.reject(t,"port ownership")

    def test_memory_response_cannot_shortcut_request_in_same_edge(self):
        t = trace()
        row = find(t,lambda s:s.get("pm_req_valid_o") and s.get("trace_pm_owner_o") == 1)
        row.update(pm_rsp_valid_i=1,pm_rsp_ready_o=1)
        self.reject(t,"memory single|response before")

    def test_memory_response_and_new_request_cannot_refill_same_edge(self):
        t = trace()
        row = find(t,lambda s:s.get("pm_rsp_valid_i"))
        row.update(pm_req_valid_o=1,pm_req_ready_i=1)
        self.reject(t,"single outstanding")

    def test_prefetch_cannot_overwrite_single_instruction_holding(self):
        t = trace("empty_local")
        row = find(t,lambda s:s["seq_o"] == generate.contract()["sequencer"]["DECODE"])
        row.update(pm_req_valid_o=1,pm_req_ready_i=1,trace_pm_owner_o=1,pm_req_address_o=128)
        self.reject(t,"prefetch")

    def test_configuration_generation_must_match(self):
        t = trace()
        row = find(t,lambda s:s.get("cfg_req_valid_i") and s["cfg_req_op_i"] == 1)
        row["cfg_req_generation_i"] = 2
        self.reject(t,"configuration generation")

    def test_fetch_uses_instruction_PC_not_byte_PC(self):
        t = trace()
        row = find(t,lambda s:s.get("pm_req_valid_o") and s.get("trace_pm_owner_o") == 1)
        row["trace_pc_o"] = 128
        self.reject(t,"fetch PC")

    def test_retire_PC_must_match_fetched_word(self):
        t = trace()
        row = find(t,lambda s:s.get("trace_retire_o"))
        row["trace_pc_o"] = 17
        self.reject(t,"retiring PC")

    def test_retire_opcode_must_match_fetched_word(self):
        t = trace()
        row = find(t,lambda s:s.get("trace_retire_o"))
        row["trace_opcode_o"] = 0
        self.reject(t,"retiring PC")

    def test_native_done_cannot_appear_before_service_acceptance(self):
        t = trace()
        row = find(t,lambda s:s["seq_o"] == generate.contract()["sequencer"]["DECODE"])
        row.update(svc_rsp_valid_i=1,svc_rsp_ready_o=1)
        self.reject(t,"response before command")

    def test_duplicate_service_completion_rejects(self):
        t = trace()
        row = find(t,lambda s:s.get("trace_retire_o") and s.get("trace_opcode_o") == 0x44)
        row.update(svc_rsp_valid_i=1,svc_rsp_ready_o=1)
        self.reject(t,"duplicate")

    def test_WAIT_cannot_consume_completion_on_response_edge(self):
        t = trace()
        row = find(t,lambda s:s.get("svc_rsp_valid_i") and s.get("svc_rsp_ready_o"))
        row.update(trace_retire_o=1,trace_opcode_o=0x44)
        self.reject(t,"prior-cycle completion")

    def test_service_response_and_new_request_have_a_bubble(self):
        t = trace()
        row = find(t,lambda s:s.get("svc_rsp_valid_i") and s.get("svc_rsp_ready_o"))
        row.update(svc_req_valid_o=1,svc_req_ready_i=1)
        self.reject(t,"single outstanding")

    def test_descriptor_snapshot_matches_image_bytes(self):
        t = trace()
        for row in t["cycles"]:
            s = row["signals"]
            if s.get("svc_req_valid_o"):
                s["svc_req_descriptor_o"] = hex(check.number(s["svc_req_descriptor_o"]) ^ 1)
        self.reject(t,"descriptor snapshot")

    def test_stale_response_epoch_rejects(self):
        t = trace()
        for row in t["cycles"]:
            s = row["signals"]
            if s.get("svc_rsp_valid_i"):
                s["svc_rsp_epoch_i"] = 2
        self.reject(t,"stale service")

    def test_terminal_cannot_hide_unconsumed_service_token(self):
        t = trace()
        row = find(t,lambda s:s.get("svc_rsp_valid_i") and s.get("svc_rsp_ready_o") == 0)
        terminal = find(t,lambda s:s.get("event_valid_o"))["event_packet_o"]
        row.update(event_valid_o=1,event_ready_i=1,event_packet_o=terminal)
        self.reject(t,"terminal service")

    def test_RX_window_snapshot_cannot_expand_object(self):
        t = trace("cancel_passive_RX_close")
        row = find(t,lambda s:s.get("svc_req_valid_o"))
        row["svc_req_object_length_o"] = 32
        self.reject(t,"object window")

    def test_RX_close_ACK_requires_prior_request_edge(self):
        t = trace("cancel_passive_RX_close")
        row = find(t,lambda s:s.get("close_req_valid_o"))
        row.update(close_rsp_valid_i=1,close_rsp_ready_o=1,close_rsp_job_i=7,
                   close_rsp_epoch_i=1,close_rsp_task_sequence_i=1)
        self.reject(t,"close ACK")

    def test_cancel_cleanup_cannot_precede_RX_close_ACK(self):
        t = trace("cancel_passive_RX_close")
        row = find(t,lambda s:s.get("close_req_valid_o"))
        row["trace_cancel_token_retire_o"] = 1
        self.reject(t,"cleanup before")

    def test_cancel_object_drop_cannot_precede_token_cleanup(self):
        t = trace("cancel_passive_RX_close")
        row = find(t,lambda s:s.get("close_req_valid_o"))
        row["trace_cancel_object_drop_o"] = 1
        self.reject(t,"outstanding service")

    def test_poison_is_sticky_until_reset(self):
        t = trace("empty_local")
        index = next(i for i,r in enumerate(t["cycles"]) if r["signals"].get("task_valid_i"))
        t["cycles"] = t["cycles"][:index+1]
        base = dict(life_o=check.LIFE["RUNNING"],deploy_valid_i=1,deploy_generation_i=1,image_valid_o=1)
        t["cycles"].append(dict(cycle=len(t["cycles"]),signals=base))
        for value in (1,0):
            t["cycles"].append(dict(cycle=len(t["cycles"]),signals=dict(
                life_o=check.LIFE["POISONED"],poison_o=value,deploy_valid_i=1,deploy_generation_i=1)))
        self.reject(t,"poison not sticky",False)

    def test_reset_needs_fresh_external_certificate(self):
        t = trace("prepare_then_deploy")
        t["cycles"].append(dict(cycle=len(t["cycles"]),signals=dict(rst_ni=0)))
        t["cycles"].append(dict(cycle=len(t["cycles"]),signals=dict(
            release_valid_i=1,release_ready_o=1,release_sequence_i=1,release_epoch_i=1)))
        self.reject(t,"stale release",False)

    def test_first_flit_is_not_packet_acceptance(self):
        f = copy.deepcopy(EXAMPLES["flit_example"])
        next(r for r in f["cycles"] if r["ready"])["packet_accepted"] = True
        with self.assertRaisesRegex(ValueError,"last flit"):
            check.check_flits(bytes.fromhex(f["packet_hex"]),f["cycles"])

    def test_partial_packet_cannot_complete(self):
        f = EXAMPLES["flit_example"]
        with self.assertRaisesRegex(ValueError,"partial packet"):
            check.check_flits(bytes.fromhex(f["packet_hex"]),f["cycles"][:-1])

    def test_held_flit_cannot_change(self):
        f = copy.deepcopy(EXAMPLES["flit_example"])
        f["cycles"][1]["data"] = "0x7"
        with self.assertRaisesRegex(ValueError,"held flit"):
            check.check_flits(bytes.fromhex(f["packet_hex"]),f["cycles"])


if __name__ == "__main__":
    unittest.main()
