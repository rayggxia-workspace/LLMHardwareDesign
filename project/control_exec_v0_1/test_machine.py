import ast
import copy
import json
import pathlib
import unittest
from unittest import mock
import compare
import machine
import run_campaign

BUNDLES,PEERS = run_campaign.inputs()


def runtime(index=2,profile=1,**updates):
    env = run_campaign.environment(PEERS,profile)
    env.update(updates)
    return machine.Machine(machine.loader.load_reference(copy.deepcopy(BUNDLES[index])),env)


def accepted(report,kind):
    return [e for e in report["events"] if e["event"]["kind"] == kind
            and (e["kind"] == "state" or e["ready"])]


def replace_image(bundle,target,data):
    b = copy.deepcopy(bundle)
    b["images_hex"][target] = data.hex()
    b["manifest"]["images"][target].update(bytes=len(data),sha256=machine.image.digest(data))
    b["manifest_sha256"] = machine.image.manifest_digest(b["manifest"])
    return b


def assemble_changed(bundle,target,program):
    d = bytes.fromhex(bundle["images_hex"][target])
    parsed = machine.image.parse_image(d)
    records = {k:v for k,v in parsed["records"].items() if k != "instruction"}
    h = parsed["header"]
    data = machine.image.assemble_image(parsed["role"],program,records,h["program_image_id"],h["resource_mask"])
    return replace_image(bundle,target,data)


class ExecutionTests(unittest.TestCase):
    def test_nine_saved_runs_rebuild_and_pass_independent_checks(self):
        result = run_campaign.campaign()
        saved = json.loads((machine.HERE/"run_reports.json").read_bytes().decode("utf-8"))
        self.assertEqual(saved,result)
        self.assertEqual(result["total_runs"],9)
        self.assertEqual(result["instructions_retired"],100)
        self.assertFalse(result["rtl_tested"])

    def test_runtime_does_not_import_or_read_reference_fixtures(self):
        source = (machine.HERE/"machine.py").read_bytes().decode("utf-8")
        tree = ast.parse(source)
        imports = [n.name for node in ast.walk(tree) if isinstance(node,ast.Import) for n in node.names]
        self.assertFalse(set(imports)&{"oracle","compare","run_campaign"})
        for forbidden in ["cases.json","golden_traces.json","expected_local_events"]:
            self.assertNotIn(forbidden,source)
        self.assertNotIn("build_bundles",source)
        with mock.patch.object(compare.oracle,"cases",side_effect=AssertionError("reference accessed")), \
             mock.patch.object(compare.oracle,"golden_traces",side_effect=AssertionError("golden accessed")), \
             mock.patch.object(compare.oracle,"check_trace",side_effect=AssertionError("oracle used to execute")):
            for index in range(3):
                self.assertEqual(runtime(index).run()["outcome"],"success")

    def test_each_nominal_program_retires_all_binary_PCs_once(self):
        for index in range(3):
            m = runtime(index,0)
            r = m.run()
            compare.check_report(run_campaign.expected_case(r["bundle"]),r)
            for target,data in m.images.items():
                h = machine.codec.unpack_record("image_header",data[:128])
                retired = [x for x in r["retired"] if x["target"] == target]
                self.assertEqual([x["pc"] for x in retired],list(range(h["instruction_count"])))
                for row in retired:
                    offset = h["instruction_offset"]+row["pc"]*16
                    self.assertEqual(row["word_hex"],data[offset:offset+16].hex())

    def test_new_binary_MOVI_changes_CALL_without_any_reference_program_dispatch(self):
        b = BUNDLES[0]
        p = machine.image.parse_image(bytes.fromhex(b["images_hex"]["mother"]))["program"]
        changed = assemble_changed(b,"mother",[dict(op="G_MOVI",a=0,x=85)]+p)
        m = machine.Machine(machine.loader.load_reference(changed))
        r = m.run()
        call = machine.codec.unpack_record("task_message",bytes.fromhex(accepted(r,"call")[0]["payload"]["hex"]))
        self.assertEqual(call["arg0"],85)
        self.assertEqual(len(r["retired"]),5)
        self.assertEqual(r["cpu"]["local0"]["arguments"],[0]*8)
        with self.assertRaisesRegex(ValueError,"CALL tuple"):
            compare.check_report(run_campaign.expected_case(r["bundle"]),r)

    def test_changed_local_MOVI_is_executed_and_independent_oracle_detects_difference(self):
        b = BUNDLES[2]
        p = machine.image.parse_image(bytes.fromhex(b["images_hex"]["local1"]))["program"]
        p[2]["x"] = 2
        changed = assemble_changed(b,"local1",p)
        r = machine.Machine(machine.loader.load_reference(changed),
                            run_campaign.environment(PEERS,0)).run()
        self.assertEqual(r["cpu"]["mother"]["registers"][0],2)
        with self.assertRaisesRegex(ValueError,"READY tuple"):
            compare.check_report(run_campaign.expected_case(r["bundle"]),r)

    def test_same_bytes_run_under_eight_stall_seeds(self):
        for seed in range(8):
            for index in range(3):
                m = runtime(index,seed=seed,random_stall_max=3)
                r = m.run()
                self.assertEqual(r["outcome"],"success")
                compare.check_report(run_campaign.expected_case(r["bundle"]),r)

    def test_alternate_local_scheduler_order_preserves_protocol(self):
        r = runtime(local_order=["local1","local0"]).run()
        compare.check_report(run_campaign.expected_case(r["bundle"]),r)

    def test_READY_acceptance_and_consumption_precede_producer_CALL(self):
        r = runtime(stalls={"return.1":6}).run()
        ready = accepted(r,"ready")[0]
        consumed = accepted(r,"consume_ready")[0]
        source_call = next(e for e in accepted(r,"call") if e["event"]["task"] == "0")
        self.assertLessEqual(ready["tick"],consumed["tick"])
        self.assertLess(consumed["tick"],source_call["tick"])
        compare.check_report(run_campaign.expected_case(r["bundle"]),r)

    def test_READY_scalar_becomes_mother_R0_and_CALL_snapshot_then_is_masked_locally(self):
        r = runtime().run()
        call = next(e for e in accepted(r,"call") if e["event"]["task"] == "0")
        msg = machine.codec.unpack_record("task_message",bytes.fromhex(call["payload"]["hex"]))
        self.assertEqual(msg["arg0"],1)
        self.assertEqual(r["cpu"]["mother"]["registers"][0],1)
        self.assertEqual(r["cpu"]["local0"]["registers"],[0]*8)
        self.assertEqual(r["cpu"]["local0"]["arguments"],[0]*8)

    def test_native_command_and_response_payload_remain_held(self):
        r = runtime(1,stalls={"M.0.command":3,"M.0.response":5}).run()
        for channel,count in [("M.0.command",4),("M.0.response",6)]:
            samples = [e for e in r["events"] if e.get("channel") == channel]
            self.assertEqual(len(samples),count)
            self.assertEqual([e["ready"] for e in samples],[False]*(count-1)+[True])
            self.assertTrue(all(e["payload"] == samples[0]["payload"] and e["event"] == samples[0]["event"]
                                for e in samples))
        compare.check_report(run_campaign.expected_case(r["bundle"]),r)

    def test_command_acceptance_does_not_complete_WAIT(self):
        r = runtime(1,latency={"native":11,"store":2,"ack":4}).run()
        cmd,rsp,wait = [accepted(r,k)[0] for k in ("native_cmd","native_rsp","wait")]
        self.assertGreaterEqual(rsp["tick"]-cmd["tick"],11)
        self.assertGreaterEqual(wait["tick"],rsp["tick"])
        self.assertGreater(r["cpu"]["local0"]["fetch_reads"],r["cpu"]["local0"]["steps"])
        self.assertEqual(r["cpu"]["local0"]["steps"],3)

    def test_data_is_actually_copied_through_finite_S_bytes(self):
        m = runtime()
        initial = bytes(m.sram[0][:32])
        self.assertEqual(initial,b"\xcd"*32)
        r = m.run()
        expected = bytes.fromhex(PEERS["ingress"][0]["data_hex"])
        self.assertEqual(bytes(m.sram[0][:16]),expected)
        self.assertEqual(bytes(m.sram[1][:16]),expected)
        self.assertEqual(bytes(m.sram[1][16:32]),b"\xcd"*16)
        self.assertEqual(len(m.sram[0]),16384)
        self.assertEqual(len(m.sram[1]),16384)
        self.assertTrue(all(v == 0 for v in r["final_activity"].values()))

    def test_write_confirmation_precedes_ACK_and_TX_release(self):
        r = runtime(latency={"native":2,"store":8,"ack":7},stalls={"source.ack":5}).run()
        data = next(e for e in accepted(r,"data") if e["event"]["pair"] == "0:1:12")
        store = next(e for e in accepted(r,"store_ack") if e["event"]["pair"] == "0:1:12")
        ack_send = next(e for e in accepted(r,"ack_send") if e["event"]["pair"] == "0:1:12")
        ack_recv = accepted(r,"ack_recv")[0]
        finish = accepted(r,"finish_tx")[0]
        drop = next(e for e in accepted(r,"drop") if e["event"]["task"] == "0")
        self.assertGreaterEqual(store["tick"]-data["tick"],8)
        self.assertGreater(ack_send["tick"],store["tick"])
        self.assertGreater(ack_recv["tick"],ack_send["tick"])
        self.assertGreaterEqual(finish["tick"],ack_recv["tick"])
        self.assertGreater(drop["tick"],ack_recv["tick"])
        compare.check_report(run_campaign.expected_case(r["bundle"]),r)

    def test_token_zero_reuse_has_new_service_sequence(self):
        r = runtime().run()
        starts = [e for e in r["events"] if e["event"]["kind"] in ("arm_rx","arm_tx")
                  and e["event"]["task"] == "0"]
        self.assertEqual([e["event"]["service_sequence"] for e in starts],[0,1])
        self.assertEqual(r["cpu"]["local0"]["steps"],7)

    def test_native_clear_preserves_nonzero_scale(self):
        m = runtime(1)
        self.assertTrue(m.native_state[0]["a_valid"])
        scale = m.native_state[0]["scale"]
        r = m.run()
        self.assertFalse(m.native_state[0]["a_valid"])
        self.assertFalse(m.native_state[0]["merged_valid"])
        self.assertEqual(m.native_state[0]["scale"],scale)
        compare.check_report(run_campaign.expected_case(r["bundle"]),r)

    def test_peer_error_returns_status9_and_never_retires_END(self):
        r = runtime(1,2).run()
        compare.check_report(run_campaign.expected_case(r["bundle"]),r,"error")
        message = machine.codec.unpack_record("event_message",bytes.fromhex(accepted(r,"terminal")[0]["payload"]["hex"]))
        self.assertEqual((message["kind"],message["status"],message["error_pc"]),(3,9,0))
        self.assertEqual(len(r["retired"]),4)
        self.assertFalse(any(x["op"] in ("L_END","G_END") for x in r["retired"]))
        self.assertEqual(len(accepted(r,"global_error")),1)

    def test_two_jobs_without_reset_preserve_RAM_and_increment_task_sequence(self):
        m = runtime()
        generation = m.loader.generation
        first = m.run(job=8)
        before = bytes(m.sram[1])
        m.environment["ingress"][0]["data_hex"] = "ff"*16
        second = m.run(job=9)
        compare.check_report(run_campaign.expected_case(first["bundle"],job=8),first)
        self.assertEqual(second["cpu"]["local0"]["task_sequence"],2)
        self.assertEqual(second["cpu"]["local1"]["task_sequence"],2)
        self.assertEqual(m.loader.generation,generation)
        self.assertEqual(m.jobs_completed,2)
        self.assertEqual(before[:16],bytes.fromhex(PEERS["ingress"][0]["data_hex"]))
        self.assertEqual(bytes(m.sram[1][:16]),b"\xff"*16)
        self.assertEqual(bytes(m.sram[1][16:]),before[16:])
        # Separate host expectation: do not obtain sequence from the runtime under test.
        definition, trace = compare.observed_trace(
            run_campaign.expected_case(second["bundle"],job=9,sequence=2),second)
        self.assertTrue(compare.oracle.check_trace(definition,trace)["reference_trace_valid"])

    def test_independent_identity_expectations_reject_stale_second_job(self):
        m = runtime()
        m.run(job=8)
        r = m.run(job=9)
        with self.assertRaisesRegex(ValueError,"sequence"):
            compare.check_report(run_campaign.expected_case(r["bundle"],job=9,sequence=1),r)
        with self.assertRaisesRegex(ValueError,"job identity"):
            compare.check_report(run_campaign.expected_case(r["bundle"],job=8,sequence=2),r)

    def test_all_service_and_return_obligations_are_empty_at_success(self):
        m = runtime()
        r = m.run()
        self.assertEqual(m.loader.state,"READY")
        self.assertFalse(m.channels or m.links or m.native or m.credits or m.ready_event)
        self.assertTrue(all(o["retired"] for o in m.operations.values()))
        self.assertTrue(all(not c.tokens and not c.objects for c in m.cpus.values()))
        self.assertLessEqual(r["peak_channels"],machine.MAX_CHANNELS)
        self.assertLessEqual(r["peak_links"],machine.MAX_LINKS)

    def test_missing_ingress_reaches_bound_without_fabricated_success(self):
        m = runtime(ingress=[])
        with self.assertRaisesRegex(machine.ModelBound,"no architectural terminal"):
            m.run(max_ticks=20)
        self.assertFalse(accepted(dict(events=m.events),"global_end"))
        self.assertEqual(m.loader.state,"INVALID")
        self.assertFalse(m.last_failure["architectural_terminal"])
        self.assertIsNone(m.last_report)

    def test_permanent_native_backpressure_does_not_fake_completion(self):
        m = runtime(1,blocked_channels=["M.0.response"])
        with self.assertRaises(machine.ModelBound):
            m.run(max_ticks=20)
        self.assertEqual(len(accepted(dict(events=m.events),"native_rsp")),0)
        self.assertEqual(len(accepted(dict(events=m.events),"wait")),0)
        self.assertFalse(any(m.loader.valid.values()))

    def test_wrong_external_packet_identity_is_rejected_before_store(self):
        m = runtime()
        m.environment["ingress"][0]["header"]["source_port"] = 1
        with self.assertRaisesRegex(ValueError,"RX packet identity"):
            m.run()
        self.assertEqual(bytes(m.sram[0][:16]),b"\xcd"*16)
        self.assertEqual(m.loader.state,"INVALID")

    def test_oversized_and_duplicate_external_packets_are_rejected(self):
        m = runtime()
        m.environment["ingress"][0]["data_hex"] = "ff"*17
        with self.assertRaisesRegex(ValueError,"payload size"):
            m.run()
        m = runtime()
        m.environment["ingress"] *= 2
        with self.assertRaisesRegex(ValueError,"route slot"):
            m.run()

    def test_partial_loader_cannot_construct_execution_instance(self):
        m = machine.loader.Loader()
        b = BUNDLES[0]
        m.begin(b["manifest"],b["manifest_sha256"])
        with self.assertRaisesRegex(ValueError,"committed READY"):
            machine.Machine(m)

    def test_reload_requires_new_execution_instance(self):
        m = runtime(0)
        b = BUNDLES[1]
        m.loader.begin(b["manifest"],b["manifest_sha256"])
        for target,text in b["images_hex"].items():
            data = bytes.fromhex(text)
            for offset in range(0,len(data),16):
                m.loader.write16(target,offset,data[offset:offset+16],m.loader.generation)
            m.loader.verify(target,m.loader.generation)
        m.loader.commit(m.loader.generation)
        with self.assertRaisesRegex(ValueError,"image changed"):
            m.run()
        self.assertEqual(m.loader.state,"READY")

    def test_unexpected_configuration_and_experiment_bounds_are_rejected(self):
        for env in (dict(random_stall_max=9),dict(native_error=1),dict(pc_script=[])):
            with self.assertRaises(ValueError):
                runtime(**env)
        m = runtime(0)
        for kwargs in (dict(job=0),dict(epoch=0),dict(max_ticks=0)):
            with self.assertRaises(ValueError):
                m.run(**kwargs)
        self.assertEqual(m.loader.state,"READY")


if __name__ == "__main__":
    unittest.main()
