import copy
import json
import unittest
import check_recovery
import recovery
import run_campaign
import run_recovery

BUNDLES,PEERS = run_campaign.inputs()


def model(index=1,**updates):
    env = run_campaign.environment(PEERS,1)
    env.update(updates)
    return recovery.RecoveryMachine(recovery.machine.loader.load_reference(BUNDLES[index]),env)


def accepted(report,kind):
    return [e for e in report["events"] if e["event"]["kind"] == kind and
            (e["kind"] == "state" or e["ready"])]


def poison(index=1):
    m = model(index,latency={"native":20,"store":2,"ack":4},
              blocked_channels=["M.0.response"] if index == 1 else ["source.ack"])
    trigger = dict(kind="native_cmd") if index == 1 else dict(kind="ack_send",pair="0:1:12")
    report = m.run(recovery=dict(trigger=trigger,drain_ticks=4))
    return m,report


def reset_complete(m,**kwargs):
    session = m.begin_reset(**kwargs)
    for _ in range(20):
        if session.tick():
            break
    return session


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campaign = run_recovery.campaign()
        cls.reports = {x["name"]:x for x in cls.campaign["experiments"]}

    def test_nine_cancellation_and_nine_resumed_runs_rebuild(self):
        saved = json.loads((recovery.machine.HERE/"recovery_reports.json").read_bytes().decode("utf-8"))
        self.assertEqual(saved,self.campaign)
        self.assertEqual(self.campaign["cancellation_runs"],9)
        self.assertEqual(self.campaign["resumed_runs"],9)
        self.assertEqual(self.campaign["reset_cohorts"],2)

    def test_CALL_held_is_not_withdrawn_and_no_local_program_is_started(self):
        r = self.reports["cancel_CALL_held"]["cancel"]
        rows = [e for e in r["events"] if e["event"]["kind"] == "call"]
        self.assertGreater(len(rows),1)
        self.assertTrue(all(e["payload"] == rows[0]["payload"] for e in rows))
        self.assertEqual([x["op"] for x in r["retired"]],["G_CALL"])
        terminal = recovery.codec.unpack_record("event_message",bytes.fromhex(accepted(r,"terminal")[0]["payload"]["hex"]))
        self.assertEqual((terminal["kind"],terminal["status"]),(3,11))

    def test_native_cancel_waits_for_real_response_acceptance(self):
        r = self.reports["cancel_native_pending"]["cancel"]
        rsp = accepted(r,"native_rsp")[0]
        wait = accepted(r,"cancel_wait")[0]
        terminal = accepted(r,"terminal")[0]
        self.assertLessEqual(rsp["tick"],wait["tick"])
        self.assertLess(wait["tick"],terminal["tick"])
        self.assertFalse(any(x["op"] in ("L_WAIT","L_END","G_END") for x in r["retired"]))

    def test_passive_RX_requires_source_close_ACK_and_never_fakes_store(self):
        r = self.reports["cancel_passive_RX"]["cancel"]
        log = r["recovery"]["control_log"]
        request = next(x for x in log if x["kind"] == "RX_close_request")
        ack = next(x for x in log if x["kind"] == "RX_close_ack")
        self.assertGreater(ack["wall_tick"],request["wall_tick"])
        self.assertTrue(ack["source_gate_closed"])
        self.assertEqual(len(accepted(r,"store_ack")),0)
        self.assertEqual(len(accepted(r,"finish_rx")),0)
        self.assertTrue(accepted(r,"cancel_wait")[0]["event"]["closed"])
        self.assertEqual({e["event"]["task"] for e in accepted(r,"call")},{"1"})

    def test_cancel_after_write_keeps_bytes_and_reports_confirmed_prefix(self):
        m = model(2)
        r = m.run(recovery=dict(trigger=dict(kind="store_ack",pair="255:0:11"),drain_ticks=64))
        self.assertEqual(bytes(m.sram[0][:16]),bytes.fromhex(PEERS["ingress"][0]["data_hex"]))
        self.assertEqual(bytes(m.sram[1][:16]),b"\xcd"*16)
        terminal = next(e for e in accepted(r,"terminal") if e["event"]["task"] == "0")
        msg = recovery.codec.unpack_record("event_message",bytes.fromhex(terminal["payload"]["hex"]))
        self.assertEqual((msg["status"],msg["flags"],msg["confirmed_write_bytes"]),(11,6,16))
        check_recovery.check_cancel(r,BUNDLES[2])

    def test_DATA_held_drains_through_remote_ACK_before_source_release(self):
        r = self.reports["cancel_DATA_held"]["cancel"]
        data = [e for e in r["events"] if e.get("channel") == "0:1:12.data"]
        self.assertTrue(any(not e["ready"] for e in data))
        self.assertTrue(all(e["payload"] == data[0]["payload"] for e in data))
        ack = accepted(r,"ack_recv")[0]
        drop = next(e for e in accepted(r,"cancel_drop") if e["event"]["task"] == "0")
        self.assertLessEqual(ack["tick"],drop["tick"])
        self.assertEqual(r["recovery"]["confirmed"]["0"],dict(read=16,write=16))

    def test_prelocked_success_DONE_is_preserved_during_job_cancellation(self):
        r = self.reports["cancel_DONE_held"]["cancel"]
        rows = [e for e in r["events"] if e["event"]["kind"] == "terminal"]
        self.assertTrue(all(e["payload"] == rows[0]["payload"] for e in rows))
        msg = recovery.codec.unpack_record("event_message",bytes.fromhex(rows[-1]["payload"]["hex"]))
        self.assertEqual((msg["kind"],msg["status"]),(2,0))
        self.assertEqual(r["recovery"]["supervisor_status"],11)
        self.assertEqual(len(accepted(r,"cancel")),0)
        self.assertEqual(len(accepted(r,"global_end")),0)

    def test_native_error_takes_precedence_over_CANCELLED(self):
        m = model(native_error=True)
        r = m.run(recovery=dict(trigger=dict(kind="native_cmd"),drain_ticks=64))
        msg = recovery.codec.unpack_record("event_message",bytes.fromhex(accepted(r,"terminal")[0]["payload"]["hex"]))
        self.assertEqual((msg["status"],msg["error_pc"]),(9,0))
        self.assertEqual(r["outcome"],"cancelled_with_error")
        self.assertEqual(r["recovery"]["supervisor_status"],9)
        check_recovery.check_cancel(r,BUNDLES[1])

    def test_poison_has_status13_and_does_not_forge_a_drained_terminal(self):
        m,r = poison()
        self.assertEqual((r["outcome"],r["recovery"]["supervisor_status"]),("reset_required",13))
        self.assertTrue(any(r["final_activity"].values()))
        self.assertEqual(m.jobs_completed,0)
        self.assertEqual(len(accepted(r,"terminal")),0)
        self.assertTrue(m.loader.needs_reset_ack)
        self.assertFalse(any(m.loader.valid.values()))
        self.assertTrue(all(p.quarantined for p in m.ports.values()))
        with self.assertRaisesRegex(ValueError,"recovery/reload"):
            m.run(job=8,epoch=2)
        with self.assertRaises(ValueError):
            m.loader.begin(BUNDLES[1]["manifest"],BUNDLES[1]["manifest_sha256"])

    def test_missing_one_RESET_ACK_keeps_cohort_closed(self):
        m,_ = poison()
        session = m.begin_reset(blocked={"M.0"})
        for _ in range(8):
            session.tick()
        self.assertFalse(session.complete)
        self.assertEqual(session.report()["pending"],["M.0"])
        self.assertTrue(m.loader.needs_reset_ack)
        with self.assertRaises(ValueError):
            m.reload_after_reset(BUNDLES[1])
        check_recovery.check_reset(session.report(),BUNDLES[1])

    def test_reset_coverage_includes_every_provider_adapter_controller_and_transport(self):
        for index,count in [(1,7),(2,11)]:
            m,_ = poison(index)
            session = reset_complete(m,delays={"M.0":4})
            self.assertEqual(len(session.acks),count)
            self.assertEqual(session.acks,check_recovery.reset_participants(BUNDLES[index]))
            self.assertTrue(session.complete)
            check_recovery.check_reset(session.report(),BUNDLES[index])

    def test_RESET_ACK_before_actual_reset_old_unknown_duplicate_and_bool_rejected(self):
        m,_ = poison()
        s = m.begin_reset(blocked={"M.0"})
        for participant,sequence in [("M.0",s.sequence),("unknown",s.sequence),
                                     ("M.0",s.sequence-1),("M.0",True)]:
            with self.assertRaises(ValueError):
                s.acknowledge(participant,sequence)
        s.tick()
        s.tick()
        with self.assertRaises(ValueError):
            s.acknowledge("S.0",s.sequence)
        self.assertNotIn("M.0",s.acks)

    def test_provider_reset_flushes_all_independent_future_responses(self):
        m,_ = poison()
        m.schedule_native_wire(0,dict(rsp_data=0,rsp_error=0,rsp_saturated=0),40,"old_job_independent")
        self.assertEqual(len(m.ports[0].queue),2)
        s = reset_complete(m,delays={"M.0":4})
        flushed = next(x for x in s.report()["log"] if x["kind"] == "provider_queue_flushed" and x["participant"] == "M.0")
        self.assertEqual(flushed["count"],2)
        self.assertFalse(m.ports[0].queue or m.ports[0].context)
        self.assertEqual(m.loader.state,"INVALID")
        self.assertFalse(m.loader.needs_reset_ack)
        self.assertTrue(all(p.quarantined for p in m.ports.values()))

    def test_reset_preserves_program_and_S_bytes_instead_of_rollback(self):
        m,r = poison(2)
        before = {k:bytes(v) for k,v in m.sram.items()}
        programs = m.loader._images()
        s = reset_complete(m)
        self.assertTrue(s.complete)
        self.assertEqual({k:bytes(v) for k,v in m.sram.items()},before)
        self.assertEqual(m.loader._images(),programs)
        self.assertEqual(before[1][:16],bytes.fromhex(PEERS["ingress"][0]["data_hex"]))

    def test_full_reload_and_fresh_epoch_required_before_unquarantine(self):
        m,_ = poison()
        reset_complete(m)
        with self.assertRaises(ValueError):
            m.run(job=8,epoch=2)
        m.reload_after_reset(BUNDLES[1])
        with self.assertRaisesRegex(ValueError,"fresh epoch"):
            m.run(job=8,epoch=1)
        self.assertTrue(m.ports[0].quarantined)
        m.environment["blocked_channels"] = []
        r = m.run(job=8,epoch=2)
        case = run_recovery.host_case(BUNDLES[1],8,2,{"0":2})
        run_campaign.compare.check_report(case,r)
        self.assertFalse(m.ports[0].quarantined)
        self.assertTrue(all(x["observer_origin"] == "current_provider" for x in r["recovery"]["wire_log"]))

    def test_late_wire_before_provider_ACK_is_quarantined_not_completion(self):
        m,_ = poison()
        m.schedule_native_wire(0,dict(rsp_data=0,rsp_error=0,rsp_saturated=0),1,"independent_old")
        s = m.begin_reset(delays={"M.0":4})
        s.tick()
        self.assertTrue(m.wire_log[-1]["quarantined"])
        self.assertFalse(m.operations["0:0"]["done"])
        self.assertFalse(s.violation)
        for _ in range(5):
            if s.tick():
                break
        self.assertTrue(s.complete)
        self.assertTrue(m.operations["0:0"]["aborted_by_reset"])
        self.assertFalse(m.operations["0:0"]["retired"])

    def test_wire_after_provider_ACK_revokes_incomplete_certificate(self):
        m,_ = poison()
        s = m.begin_reset(delays={"M.0":1},blocked={"S.0"})
        s.tick()
        m.schedule_native_wire(0,dict(rsp_data=0,rsp_error=0,rsp_saturated=0),1,"violating_provider")
        s.tick()
        self.assertTrue(s.violation)
        self.assertEqual(m.lifecycle,"POISONED")
        self.assertIsNone(m.certificate)
        self.assertTrue(m.loader.needs_reset_ack)
        second = m.begin_reset()
        with self.assertRaises(ValueError):
            second.acknowledge("M.0",s.sequence)

    def test_late_wire_after_reset_before_reload_invalidates_certificate(self):
        m,_ = poison()
        reset_complete(m)
        m.schedule_native_wire(0,dict(rsp_data=0,rsp_error=0,rsp_saturated=0),1,"late_after_ACK")
        m.advance_idle()
        self.assertEqual(m.lifecycle,"POISONED")
        self.assertIsNone(m.certificate)
        with self.assertRaises(ValueError):
            m.reload_after_reset(BUNDLES[1])

    def test_late_wire_after_reload_before_new_job_invalidates_valid_bits(self):
        m,_ = poison()
        reset_complete(m)
        m.reload_after_reset(BUNDLES[1])
        self.assertTrue(any(m.loader.valid.values()))
        m.schedule_native_wire(0,dict(rsp_data=0,rsp_error=0,rsp_saturated=0),0,"late_after_reload")
        m.advance_idle()
        self.assertFalse(any(m.loader.valid.values()))
        self.assertEqual(m.loader.state,"INVALID")
        with self.assertRaises(ValueError):
            m.run(job=8,epoch=2)

    def test_idle_untagged_wire_poison_does_not_rewrite_prior_success(self):
        m = model(0)
        first = m.run()
        m.schedule_native_wire(0,dict(rsp_data=0,rsp_error=0,rsp_saturated=0),1,"old_after_job")
        m.advance_idle()
        self.assertEqual(m.lifecycle,"POISONED")
        self.assertEqual(first["outcome"],"success")
        self.assertEqual(len(accepted(first,"global_end")),1)
        self.assertEqual(len(m.wire_log),1)
        self.assertTrue(m.wire_log[0]["quarantined"])

    def test_unlabeled_old_response_during_new_context_is_inherently_ambiguous(self):
        class ViolatingSource(recovery.RecoveryMachine):
            def _accepted(self,pending):
                super()._accepted(pending)
                if pending["action"] == "native_cmd":
                    self.schedule_native_wire(0,dict(rsp_data=0,rsp_error=0,rsp_saturated=0),1,"old_job")
        env = run_campaign.environment(PEERS,0)
        env["latency"]["native"] = 20
        m = ViolatingSource(recovery.machine.loader.load_reference(BUNDLES[1]),env)
        r = m.run(recovery=dict(trigger=dict(kind="native_cmd"),drain_ticks=5))
        old = next(w for w in r["recovery"]["wire_log"] if w["observer_origin"] == "old_job")
        self.assertFalse(old["quarantined"])  # observer label is not a native hardware tag
        self.assertEqual(old["context"],"0:0")
        self.assertFalse({"job","epoch"} & set(old["payload"]))
        self.assertEqual(r["outcome"],"reset_required")  # remaining provider work blocks clean drain

    def test_model_bound_enters_poison_and_can_start_coordinated_reset(self):
        m = model(2,ingress=[])
        with self.assertRaises(recovery.machine.ModelBound):
            m.run(max_ticks=12)
        self.assertEqual(m.lifecycle,"POISONED")
        self.assertTrue(m.begin_reset())

    def test_native_source_queue_has_a_real_finite_capacity(self):
        p = recovery.NativePort()
        wire = dict(rsp_data=0,rsp_error=0,rsp_saturated=0)
        p.schedule(wire,2,"a")
        p.schedule(wire,3,"b")
        with self.assertRaisesRegex(ValueError,"queue full"):
            p.schedule(wire,4,"c")

    def test_independent_checker_rejects_new_instruction_after_cancel(self):
        r = copy.deepcopy(self.reports["cancel_native_pending"]["cancel"])
        r["retired"].append(dict(target="local0",pc=2,word_hex="ff"*16,op="L_END"))
        with self.assertRaisesRegex(ValueError,"new instruction"):
            check_recovery.check_cancel(r,BUNDLES[1])

    def test_independent_checker_rejects_missing_native_response_before_cancel_retire(self):
        r = copy.deepcopy(self.reports["cancel_native_pending"]["cancel"])
        r["events"] = [e for e in r["events"] if e["event"]["kind"] != "native_rsp"]
        with self.assertRaisesRegex(ValueError,"unfinished service"):
            check_recovery.check_cancel(r,BUNDLES[1])

    def test_independent_checker_rejects_held_packet_change(self):
        r = copy.deepcopy(self.reports["cancel_CALL_held"]["cancel"])
        event = next(e for e in r["events"] if e["event"]["kind"] == "call" and not e["ready"])
        event["payload"]["hex"] = "ff"*64
        with self.assertRaisesRegex(ValueError,"held packet"):
            check_recovery.check_cancel(r,BUNDLES[0])

    def test_independent_checker_rejects_forged_success_after_cancel(self):
        r = copy.deepcopy(self.reports["cancel_native_pending"]["cancel"])
        for e in r["events"]:
            if e["event"]["kind"] == "terminal":
                msg = recovery.codec.unpack_record("event_message",bytes.fromhex(e["payload"]["hex"]))
                msg.update(kind=2,status=0)
                e["payload"]["hex"] = recovery.codec.pack_record("event_message",msg).hex()
        with self.assertRaisesRegex(ValueError,"new success terminal"):
            check_recovery.check_cancel(r,BUNDLES[1])

    def test_independent_checker_rejects_mutated_prefix_even_if_message_matches_bad_ledger(self):
        r = copy.deepcopy(self.reports["cancel_after_ingress_write"]["cancel"])
        r["recovery"]["confirmed"]["0"]["write"] = 0
        for e in r["events"]:
            if e["event"]["kind"] == "terminal" and e["event"]["task"] == "0":
                msg = recovery.codec.unpack_record("event_message",bytes.fromhex(e["payload"]["hex"]))
                msg["confirmed_write_bytes"] = 0
                e["payload"]["hex"] = recovery.codec.pack_record("event_message",msg).hex()
        with self.assertRaisesRegex(ValueError,"prefix mismatch"):
            check_recovery.check_cancel(r,BUNDLES[2])

    def test_independent_reset_checker_rejects_shrunk_scope(self):
        r = copy.deepcopy(self.reports["poison_native_response_stuck"]["reset"]["report"])
        next(x for x in r["log"] if x["kind"] == "reset_request")["participants"].remove("M.0")
        with self.assertRaisesRegex(ValueError,"reset scope"):
            check_recovery.check_reset(r,BUNDLES[1])

    def test_reset_requires_quiet_observation_after_last_ACK(self):
        m,_ = poison()
        s = m.begin_reset()
        self.assertFalse(s.tick())
        self.assertFalse(s.tick())  # all ACKs now present, gate remains closed
        self.assertEqual(s.acks,s.participants)
        self.assertTrue(m.loader.needs_reset_ack)
        self.assertTrue(s.tick())
        self.assertFalse(m.loader.needs_reset_ack)
        report = s.report()
        check_recovery.check_reset(report,BUNDLES[1])
        last_ack = max(x["wall_tick"] for x in report["log"] if x["kind"] == "reset_ack")
        next(x for x in report["log"] if x["kind"] == "reset_complete")["wall_tick"] = last_ack
        with self.assertRaisesRegex(ValueError,"quiet observation"):
            check_recovery.check_reset(report,BUNDLES[1])
        bad = s.report()
        next(x for x in bad["log"] if x["kind"] == "reset_complete")["activity"]["untagged"] = 1
        with self.assertRaisesRegex(ValueError,"nonquiescent"):
            check_recovery.check_reset(bad,BUNDLES[1])


if __name__ == "__main__":
    unittest.main()
