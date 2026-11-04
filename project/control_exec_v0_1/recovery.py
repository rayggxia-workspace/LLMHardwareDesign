"""Bounded cancellation/reset extension. Provider reset handshakes are peers, not RTL."""
import copy
import machine

need = machine.need
codec = machine.codec


class NativePort:
    """No job/epoch/native tag on the wire. Origin is observer evidence ONLY."""
    def __init__(self):
        self.context = None
        self.quarantined = False
        self.queue = []

    def schedule(self, payload, due, origin):
        need(len(self.queue) < 2, "finite native source queue full")
        need(set(payload) == {"rsp_data","rsp_error","rsp_saturated"} and
             type(due) is int and due >= 0 and type(payload["rsp_data"]) is int and
             0 <= payload["rsp_data"] < 1 << 128 and
             payload["rsp_error"] in (0,1) and payload["rsp_saturated"] in (0,1), "native wire fields")
        self.queue.append(dict(payload=copy.deepcopy(payload),due=due,observer_origin=origin))
        self.queue.sort(key=lambda x:x["due"])

    def take(self, now):
        if self.queue and self.queue[0]["due"] <= now:
            return self.queue.pop(0)
        return None

    def reset_provider(self):
        count = len(self.queue)
        self.queue.clear()  # clear ALL future responses, never filter by an origin/tag
        return count


class RecoveryMachine(machine.Machine):
    def __init__(self, admitted_loader, environment=None):
        super().__init__(admitted_loader,environment)
        self.ports = {b:NativePort() for b in self.sequence}
        self.lifecycle = "RUNNING"
        self.wall_tick = 0
        self.reset_sequence = 0
        self.reset_session = None
        self.certificate = None
        self.control_log = []
        self.wire_log = []
        self.poison_epoch = None
        self.poison_generation = None
        self.cpus = {k:machine.CPU(k,data) for k,data in self.images.items()}
        for cpu in self.cpus.values():
            cpu.active = False
        self.channels,self.links,self.native,self.operations,self.credits = {},{},{},{},{}
        self.ready_event = None
        self.events,self.retired = [],[]
        self.tick,self.epoch = -1,0

    def _log(self, kind, **fields):
        row = dict(kind=kind,wall_tick=self.wall_tick,tick=getattr(self,"tick",-1),
                   protocol_position=len(getattr(self,"events",[])),
                   retired_position=len(getattr(self,"retired",[])))
        row.update(copy.deepcopy(fields))
        self.control_log.append(row)

    def schedule_native_wire(self, block, payload, delay, observer_origin="external"):
        need(block in self.ports and type(delay) is int and 0 <= delay <= 128, "native injection bound")
        self.ports[block].schedule(payload,self.wall_tick+delay,observer_origin)

    def _receive_ports(self):
        for block,port in self.ports.items():
            channel = "M.%d.response"%block
            if channel in getattr(self,"channels",{}):
                continue
            wire = port.take(self.wall_tick)
            if wire is None:
                continue
            # Classification uses only quarantine/context. Origin cannot influence it.
            quarantined = port.quarantined or port.context is None
            self.wire_log.append(dict(block=block,wall_tick=self.wall_tick,payload=wire["payload"],
                observer_origin=wire["observer_origin"],quarantined=quarantined,
                context=port.context))
            if quarantined:
                self._log("native_wire_quarantined",block=block,payload=wire["payload"])
                if self.lifecycle == "RESETTING" and "M.%d"%block in self.reset_session.acks:
                    self.reset_session.violate("wire after provider RESET_ACK")
                elif self.lifecycle in ("RESET_COMPLETE","RELOADED") or not port.quarantined:
                    self._poison("unexpected untagged response outside an admitted command")
                continue
            opid = port.context
            need(opid in self.native and opid in self.operations,"native adapter context missing")
            op = self.operations[opid]
            self._offer(channel,self._event("native_rsp",block,operation=opid,
                        service_sequence=op["sequence"]),wire["payload"],"native_rsp",operation=opid)

    def advance_idle(self,ticks=1):
        need(type(ticks) is int and 1 <= ticks <= 128,"idle observation bound")
        need(self.loader.state != "RUNNING","use execution scheduler while running")
        for _ in range(ticks):
            self.wall_tick += 1
            self._receive_ports()

    def run(self,job=7,epoch=1,max_ticks=256,recovery=None):
        need(self.lifecycle not in ("POISONED","RESETTING","RESET_COMPLETE"),"cohort recovery/reload incomplete")
        need(not any(p.queue or p.context for p in self.ports.values()),"native source not quiescent")
        if self.lifecycle == "RELOADED":
            need(self.certificate is not None and epoch > self.poison_epoch and
                 self.loader.generation > self.poison_generation,"fresh epoch/full reload required")
            for port in self.ports.values():
                port.quarantined = False
        self.lifecycle = "RUNNING"
        self.plan = copy.deepcopy(recovery)
        if self.plan is not None:
            need(set(self.plan) <= {"trigger","drain_ticks","close_ticks"} and
                 type(self.plan.get("drain_ticks",32)) is int and 1 <= self.plan.get("drain_ticks",32) <= 128 and
                 type(self.plan.get("close_ticks",2)) is int and 1 <= self.plan.get("close_ticks",2) <= 64,
                 "recovery experiment configuration")
        self.control_log,self.wire_log = [],[]
        self.cancel_tick = None
        self.cancel_sent,self.cancelled = set(),set()
        self.close_requests = {}
        self.confirmed = {b:dict(read=0,write=0) for b in self.sequence}
        self.write_seen = set()
        self.frozen_pending = []
        self.cancel_error_seen = False
        try:
            return super().run(job,epoch,max_ticks)
        except Exception:
            self._poison("execution experiment failed before a safe terminal")
            raise

    def activity(self):
        if not hasattr(self,"cpus"):
            return {k:0 for k in machine.loader.ACTIVITY_KEYS}
        counts = super().activity()
        counts["untagged"] = max(counts["untagged"],sum(len(p.queue) for p in self.ports.values()),
                                 sum(p.context is not None for p in self.ports.values()))
        return counts

    def _idle(self):
        return super()._idle() and not any(p.queue or p.context for p in self.ports.values())

    def _before_tick(self):
        self.wall_tick += 1
        if self.lifecycle == "RUNNING" and self.plan:
            trigger = self.plan["trigger"]
            matches = [e for e in self.events if e["event"]["kind"] == trigger["kind"]
                       and (trigger.get("task") is None or e["event"].get("task") == str(trigger["task"]))
                       and (trigger.get("pair") is None or e["event"].get("pair") == trigger["pair"])
                       and ((e["kind"] == "state" or e.get("ready")) if trigger.get("accepted",True)
                            else e["kind"] == "sample" and not e["ready"])]
            if len(matches) >= trigger.get("occurrence",1):
                self._request_cancel()
        if self.lifecycle == "CANCELLING" and self.tick-self.cancel_tick >= self.plan.get("drain_ticks",32):
            self._poison("cancel drain budget exhausted; not proof of deadlock")

    def _request_cancel(self):
        self.cancel_tick = self.tick
        self.lifecycle = "CANCELLING"
        self.cpus["mother"].active = False
        self.loader.quiesce()
        self.frozen_pending = [dict(target=p["context"].get("target","mother"),
                                   instruction=p["context"].get("instruction"),
                                   pc=self.cpus[p["context"].get("target","mother")].pc,
                                   word_hex=p["context"].get("raw"),
                                   event=copy.deepcopy(p["event"]),payload=copy.deepcopy(p["payload"]))
                               for p in self.channels.values()]
        self._log("cancel_latched",pending=self.frozen_pending,activity=self.activity())

    def _services_enabled(self):
        return self.lifecycle != "POISONED"

    def _issue_allowed(self,cpu):
        return self.lifecycle == "RUNNING"

    def _peers_step(self):
        # Native source is independent of the controller's request dictionary.
        saved_native = self.native
        saved_ingress = self.environment.get("ingress",[])
        self.native = {}
        if self.lifecycle == "CANCELLING":
            self.environment["ingress"] = []  # registered source-close gate in this peer contract
        try:
            super()._peers_step()
        finally:
            self.native = saved_native
            self.environment["ingress"] = saved_ingress
        for event in self.events:
            if event["event"]["kind"] == "store_ack" and event["name"] not in self.write_seen:
                self.write_seen.add(event["name"])
                self.confirmed[int(event["event"]["task"])]["write"] += event["event"]["bytes"]
        self._receive_ports()

    def _make_link(self,header,data,rx,tx):
        super()._make_link(header,data,rx,tx)
        if tx is not None:
            self.confirmed[tx["block"]]["read"] += len(data)
            self._log("S_read_observed",block=tx["block"],bytes=len(data))

    def _accepted(self,pending):
        action,ctx = pending["action"],pending["context"]
        if action == "cancel":
            cpu = self.cpus["local"+str(ctx["block"])]
            msg = codec.unpack_record("task_message",bytes.fromhex(pending["payload"]["hex"]))
            need(msg["kind"] == 1 and msg["job_id"] == self.job and msg["epoch"] == self.epoch and
                 msg["target_block"] == cpu.block and msg["task_sequence"] == cpu.task_sequence and
                 msg["completion_token"] == cpu.completion_token and
                 msg["program_image_id"] == cpu.header["program_image_id"] and
                 msg["topology_id"] == cpu.header["topology_id"] and msg["task_descriptor"] == 0 and
                 all(msg["arg%d"%i] == 0 for i in range(8)),"CANCEL identity/parameters")
            self.cancelled.add(cpu.block)
            self._log("cancel_accepted",block=cpu.block)
            return
        super()._accepted(pending)
        if action == "native_cmd":
            op = self.operations[ctx["operation"]]
            port = self.ports[op["block"]]
            need(port.context is None and not port.quarantined,"native issue while quarantined/busy")
            port.context = op["id"]
            port.schedule(dict(rsp_data=0,rsp_error=int(self.environment.get("native_error",False)),
                               rsp_saturated=0),self.wall_tick+self.latency("native"),"current_provider")
        elif action == "native_rsp":
            self.ports[self.operations[ctx["operation"]]["block"]].context = None

    def _after_tick(self):
        if self.lifecycle != "CANCELLING":
            return
        if self.ready_event is not None:
            self._log("cancel_discard_ready",packet=self.ready_event)
            self.ready_event = None
        # Use the existing shared command holding slot. Never retract an offered CALL.
        if "mother.call" not in self.channels:
            for block in sorted(self.sequence):
                cpu = self.cpus["local"+str(block)]
                terminal = self.channels.get("return."+str(block))
                if (not cpu.active or block in self.cancel_sent or
                    terminal is not None and terminal["action"] == "terminal"):
                    continue
                packet = dict(kind=1,target_block=block,job_id=self.job,epoch=self.epoch,
                    task_sequence=cpu.task_sequence,completion_token=cpu.completion_token,
                    task_descriptor=0,program_image_id=cpu.header["program_image_id"],
                    topology_id=cpu.header["topology_id"])
                self._offer("mother.call",self._event("cancel",block),
                            dict(hex=codec.pack_record("task_message",packet).hex()),"cancel",block=block)
                self.cancel_sent.add(block)
                break
        for block in sorted(self.cancelled):
            cpu = self.cpus["local"+str(block)]
            if not cpu.active or cpu.holding:
                continue
            for token,opid in list(cpu.tokens.items()):
                op = self.operations[opid]
                if op["kind"] == "rx" and not op["done"] and not any(l["rx"] == opid for l in self.links.values()):
                    if opid not in self.close_requests:
                        self.close_requests[opid] = self.tick+self.plan.get("close_ticks",2)
                        self._log("RX_close_request",block=block,operation=opid)
                    if self.tick >= self.close_requests[opid]:
                        need(not any(l["rx"] == opid for l in self.links.values()),"RX close race")
                        op.update(done=True,cancel_closed=True)
                        self._log("RX_close_ack",block=block,operation=opid,source_gate_closed=True)
                if op["done"]:
                    self._state("cancel_wait",block,operation=opid,service_sequence=op["sequence"],
                                closed=op.get("cancel_closed",False))
                    op["retired"] = True
                    del cpu.tokens[token]
                    if op["error"]:
                        cpu.error_pc = op["issue_pc"]
            if cpu.tokens:
                continue
            for oid in list(cpu.objects):
                self._state("cancel_drop",block,object=oid)
                del cpu.objects[oid]
            count = self.confirmed[block]
            status = 9 if cpu.error_pc is not None else 11
            packet = codec.pack_record("event_message",dict(kind=3,source_block=block,
                job_id=self.job,epoch=self.epoch,task_sequence=cpu.task_sequence,
                completion_token=cpu.completion_token,status=status,
                flags=4 | (2 if count["write"] else 0),
                confirmed_read_bytes=count["read"],confirmed_write_bytes=count["write"],
                error_pc=cpu.error_pc if status == 9 else 0xffffffff))
            cpu.holding = True
            self._offer("return."+str(block),self._event("terminal",block),dict(hex=packet.hex()),
                        "terminal",target=cpu.target,token=cpu.completion_token,instruction=None,raw=None)
            self._log("cancel_terminal_locked",block=block,status=status,counts=count)
        for token,credit in list(self.credits.items()):
            if credit["result"] is not None:
                self.cancel_error_seen |= credit["result"]["status"] not in (0,11)
                self._state("cancel_consume_done",credit["block"])
                del self.credits[token]
        if self._idle() and not self.credits and self.ready_event is None:
            self.lifecycle = "DRAINED"
            self.outcome = "cancelled_with_error" if self.cancel_error_seen else "cancelled"
            self._log("cancel_complete",status=9 if self.cancel_error_seen else 11,activity=self.activity())

    def _poison(self,reason):
        if self.lifecycle == "POISONED":
            return
        self.poison_epoch = getattr(self,"epoch",0)
        self.poison_generation = self.loader.generation
        self.certificate = None
        for port in self.ports.values():
            port.quarantined = True
        if self.loader.state in ("RUNNING","DRAINING"):
            self.loader.observe_activity(**self.activity())
        self.loader.reset()
        self.lifecycle = "POISONED"
        self.outcome = "reset_required"
        self._log("poison",status=13,reason=reason,activity=self.activity())

    def _sync_activity(self):
        if self.lifecycle != "POISONED":
            super()._sync_activity()

    def _finish_job(self):
        if self.lifecycle == "POISONED":
            need(self.loader.state == "INVALID" and self.loader.needs_reset_ack,"poison admission gate")
        elif self.lifecycle == "DRAINED":
            need(self._idle() and not self.credits and self.ready_event is None,"cancel not drained")
            self.loader.drained()
            self.jobs_completed += 1
        else:
            super()._finish_job()

    def _extend_report(self,report):
        report["recovery"] = dict(lifecycle=self.lifecycle,
            supervisor_status=13 if self.lifecycle == "POISONED" else
                              (9 if self.cancel_error_seen else 11) if self.lifecycle == "DRAINED" else 0,
            drained=self.lifecycle != "POISONED",control_log=copy.deepcopy(self.control_log),
            wire_log=copy.deepcopy(self.wire_log),
            confirmed={str(k):copy.deepcopy(v) for k,v in self.confirmed.items()},
            cancellation_is_job_success=False,reset_sequence=self.reset_sequence)
        return report

    def begin_reset(self,delays=None,blocked=()):
        need(self.lifecycle == "POISONED","reset requires poisoned cohort")
        need(self.reset_sequence < 0xffffffff,"reset sequence wrap unsupported")
        self.reset_sequence += 1
        self.lifecycle = "RESETTING"
        self.reset_session = ResetSession(self,self.reset_sequence,delays or {},set(blocked))
        return self.reset_session

    def reload_after_reset(self,bundle):
        need(self.lifecycle == "RESET_COMPLETE" and self.certificate is not None and
             not any(p.queue or p.context for p in self.ports.values()),"full reset certificate required")
        need(set(bundle["images_hex"]) == set(self.images),"reset/reload cohort inventory changed")
        self.loader.begin(bundle["manifest"],bundle["manifest_sha256"])
        for target,text in bundle["images_hex"].items():
            data = bytes.fromhex(text)
            for offset in range(0,len(data),16):
                self.loader.write16(target,offset,data[offset:offset+16],self.loader.generation)
            self.loader.verify(target,self.loader.generation)
        self.loader.commit(self.loader.generation)
        self.images = self.loader._images()
        self.manifest_sha256 = self.loader.expected_digest
        self.lifecycle = "RELOADED"
        self._log("full_reload_committed",generation=self.loader.generation)


class ResetSession:
    def __init__(self,runtime,sequence,delays,blocked):
        self.runtime,self.sequence = runtime,sequence
        self.participants = {"controller.mother","transport","ingress"}
        for block in runtime.sequence:
            self.participants.update({"controller.local%d"%block,"adapter.%d"%block,
                                      "M.%d"%block,"S.%d"%block})
        need(set(delays) <= self.participants and blocked <= self.participants,"unknown reset participant")
        need(all(type(v) is int and 1 <= v <= 64 for v in delays.values()),"reset delay bound")
        self.delays = {p:delays.get(p,2) for p in self.participants}
        self.blocked,self.executed,self.acks = blocked,set(),set()
        self.age = 0
        self.quiet_since = None
        self.complete = False
        self.violation = None
        runtime._log("reset_request",sequence=sequence,participants=sorted(self.participants))

    def _apply_reset(self,participant):
        m = self.runtime
        if participant.startswith("M."):
            block = int(participant.split(".")[1])
            flushed = m.ports[block].reset_provider()
            m.native = {k:v for k,v in m.native.items() if m.operations[k]["block"] != block}
            m._log("provider_queue_flushed",participant=participant,count=flushed)
        elif participant.startswith("adapter."):
            m.ports[int(participant.split(".")[1])].context = None
        elif participant.startswith("controller."):
            cpu = m.cpus[participant.split(".",1)[1]]
            cpu.active,cpu.holding = False,False
            cpu.tokens.clear()
            cpu.objects.clear()
        elif participant == "transport":
            m.channels.clear()
            m.links.clear()
            m.credits.clear()
            m.ready_event = None
            for op in m.operations.values():
                if not op["retired"]:
                    op["aborted_by_reset"] = True
        # S payload and program RAM deliberately survive. No numerical reset claim.
        self.executed.add(participant)
        m._log("reset_applied",sequence=self.sequence,participant=participant)

    def acknowledge(self,participant,sequence):
        need(self.runtime.lifecycle == "RESETTING" and not self.violation,"reset session not active")
        need(type(sequence) is int and sequence == self.sequence and participant in self.participants and
             participant not in self.acks and participant in self.executed,"stale/unknown/unapplied/duplicate RESET_ACK")
        self.acks.add(participant)
        self.runtime._log("reset_ack",sequence=sequence,participant=participant)

    def violate(self,reason):
        self.violation = reason
        self.runtime._poison(reason)
        self.runtime._log("reset_certificate_revoked",sequence=self.sequence,reason=reason)

    def tick(self):
        need(not self.complete and self.runtime.lifecycle == "RESETTING","reset session not active")
        m = self.runtime
        self.age += 1
        m.wall_tick += 1
        m._receive_ports()
        if self.violation:
            return False
        for participant in sorted(self.participants-self.executed-self.blocked):
            if self.age >= self.delays[participant]:
                self._apply_reset(participant)
                self.acknowledge(participant,self.sequence)
        if self.acks == self.participants:
            if any(p.queue or p.context for p in m.ports.values()) or any(m.activity().values()):
                self.violate("RESET_ACK cohort still has pending work")
                return False
            if self.quiet_since is None:
                self.quiet_since = self.age
            elif self.age > self.quiet_since:
                m.loader.ack_cohort_reset(True)  # only after matched ACKs + actual modeled quiescence
                self.complete = True
                m.lifecycle = "RESET_COMPLETE"
                m.certificate = dict(sequence=self.sequence,participants=sorted(self.participants),
                                     epoch_floor=m.poison_epoch,generation_floor=m.poison_generation)
                m._log("reset_complete",certificate=m.certificate,activity=m.activity())
        return self.complete

    def report(self):
        return dict(sequence=self.sequence,complete=self.complete,participants=sorted(self.participants),
                    acks=sorted(self.acks),pending=sorted(self.participants-self.acks),
                    violation=self.violation,loader_state=self.runtime.loader.state,
                    log=copy.deepcopy(self.runtime.control_log))
