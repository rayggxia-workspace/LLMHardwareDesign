"""Bounded binary-fetch control interpreter with finite protocol peers.

No cases/golden/oracle import or program selection by bundle name.
Ticks are scheduler steps, not hardware clocks or performance evidence.
"""
import copy
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "control_image_v0_1"))
import image
import loader

codec = image.codec
need = image.need
SIZES = dict((n, size) for n, size, _ in image.SECTIONS)
MAX_CHANNELS = 8
MAX_LINKS = 2
MAX_OBSERVATIONS = 2048


class ModelBound(RuntimeError):
    """An experiment bound was reached; not an architectural success/failure."""


def route(header):
    return "%d:%d:%d" % (header["source_block"], header["destination_block"], header["edge_id"])


class CPU:
    def __init__(self, target, data):
        self.target = target
        self.data = data
        self.header = codec.unpack_record("image_header", data[:128])
        self.role = "mother" if self.header["role"] == 0 else "local"
        self.block = None if self.role == "mother" else int(target[5:])
        self.pc = self.header["entry_pc"]
        self.regs = [0] * 8
        self.arguments = [0] * 8
        self.active = self.role == "mother"
        self.holding = False
        self.steps = 0
        self.reads = 0
        self.tokens = {}
        self.objects = {}
        self.service_sequence = 0
        self.task_sequence = None
        self.event_sequence = 0
        self.completion_token = None
        self.task = None
        self.error_pc = None

    def record(self, name, index):
        need(type(index) is int and 0 <= index < self.header[name + "_count"], "descriptor index")
        offset = self.header[name + "_offset"] + index * SIZES[name]
        return codec.unpack_record(name, self.data[offset:offset+SIZES[name]])

    def fetch(self):
        need(0 <= self.pc < self.header["instruction_count"], "fetch PC out of range")
        offset = self.header["instruction_offset"] + self.pc * 16
        self.reads += 1
        raw = self.data[offset:offset+16]
        return codec.decode_instruction(int.from_bytes(raw, "little"), self.role), raw.hex()


class Machine:
    def __init__(self, admitted_loader, environment=None):
        need(admitted_loader.state == "READY", "execution requires committed READY loader")
        self.loader = admitted_loader
        # Read-only architectural image bytes after loading through write16/verify/commit.
        self.images = admitted_loader._images()
        self.manifest_sha256 = admitted_loader.expected_digest
        image.validate_bundle(admitted_loader.manifest, self.images)
        self.environment = copy.deepcopy(environment or {})
        need(not (set(self.environment)-{"name","seed","random_stall_max","latency","ingress","native_error",
                                        "stalls","blocked_channels","local_order"}), "unknown peer configuration")
        need(len(self.environment.get("ingress",[])) <= 2, "finite external packet source")
        need(type(self.environment.get("random_stall_max",0)) is int and
             0 <= self.environment.get("random_stall_max",0) <= 8, "random stall model bound")
        need(type(self.environment.get("native_error",False)) is bool, "native_error must be boolean")
        self.sequence = {int(k[5:]): 0 for k in self.images if k != "mother"}
        self.sram = {b: bytearray([0xcd] * 16384) for b in self.sequence}
        self.native_state = {b: dict(a_valid=True, b_valid=True, merged_valid=True,
                                    partial_valid=True, scale=0x1375) for b in self.sequence}
        self.jobs_completed = 0
        self.last_report = None

    def _event(self, kind, block=None, **fields):
        e = dict(kind=kind, job=self.job, epoch=self.epoch)
        if block is not None:
            e.update(task=str(block), task_sequence=self.cpus["local"+str(block)].task_sequence)
        e.update(fields)
        return e

    def _observe(self, kind, event, payload=None, channel=None, ready=None):
        if len(self.events) >= MAX_OBSERVATIONS:
            raise ModelBound("finite observation buffer exhausted")
        row = dict(name="e%04d" % len(self.events), tick=self.tick, kind=kind, event=copy.deepcopy(event))
        if kind == "sample":
            row.update(channel=channel, valid=True, ready=ready, payload=copy.deepcopy(payload))
        self.events.append(row)

    def _state(self, kind, block=None, **fields):
        self._observe("state", self._event(kind, block, **fields))

    def _commit(self, cpu, instruction, raw):
        limit = min(cpu.header["max_steps"], cpu.task["max_steps"] if cpu.task else 4096)
        need(cpu.steps < limit, "instruction step budget exhausted")
        self.retired.append(dict(target=cpu.target, pc=cpu.pc, word_hex=raw,
                                 op=instruction["op"], tick=self.tick, registers=list(cpu.regs)))
        cpu.pc += 1
        cpu.steps += 1
        cpu.holding = False

    def _offer(self, channel, event, payload, action, **context):
        need(channel not in self.channels and len(self.channels) < MAX_CHANNELS,
             "finite holding channel occupied/full")
        stalls = self.environment.get("stalls", {}).get(channel, self.rng.randint(
            0, self.environment.get("random_stall_max", 0)))
        need(type(stalls) is int and 0 <= stalls <= 64, "stall count outside model bound")
        self.channels[channel] = dict(event=copy.deepcopy(event), payload=copy.deepcopy(payload),
                                      action=action, context=context, stalls=stalls)
        self.peak_channels = max(self.peak_channels, len(self.channels))

    def _channels_step(self):
        for name in list(self.channels):
            pending = self.channels[name]
            action, ctx = pending["action"], pending["context"]
            ready = pending["stalls"] == 0 and name not in self.environment.get("blocked_channels", [])
            if action == "call":
                ready = ready and not self.cpus["local"+str(ctx["block"])].active
            elif action == "ready":
                ready = ready and self.ready_event is None
            elif action == "terminal":
                ready = ready and self.credits[ctx["token"]]["result"] is None
            self._observe("sample", pending["event"], pending["payload"], name, bool(ready))
            if pending["stalls"]:
                pending["stalls"] -= 1
            if ready:
                del self.channels[name]
                self._accepted(pending)

    def _accepted(self, pending):
        action, ctx = pending["action"], pending["context"]
        if action == "call":
            cpu = self.cpus["local"+str(ctx["block"])]
            msg = codec.unpack_record("task_message", bytes.fromhex(pending["payload"]["hex"]))
            need(not cpu.active and not cpu.tokens and not cpu.objects and
                 msg["task_sequence"] == self.sequence[cpu.block]+1 and
                 msg["job_id"] == self.job and msg["epoch"] == self.epoch and
                 msg["program_image_id"] == cpu.header["program_image_id"] and
                 msg["topology_id"] == cpu.header["topology_id"], "CALL admission identity/state")
            cpu.task = cpu.record("task", msg["task_descriptor"])
            cpu.pc = cpu.task["entry_pc"]
            cpu.regs = [0] * 8
            cpu.arguments = [msg["arg%d" % i] if cpu.task["argument_mask"] & (1 << i) else 0 for i in range(8)]
            cpu.task_sequence = msg["task_sequence"]
            cpu.completion_token = msg["completion_token"]
            cpu.active = True
            self.sequence[cpu.block] = cpu.task_sequence
            self._commit(self.cpus["mother"], ctx["instruction"], ctx["raw"])
        elif action == "ready":
            cpu = self.cpus[ctx["target"]]
            msg = codec.unpack_record("event_message", bytes.fromhex(pending["payload"]["hex"]))
            need(self.ready_event is None and msg["task_sequence"] == cpu.task_sequence,
                 "READY identity/slot")
            self.ready_event = msg
            self._commit(cpu, ctx["instruction"], ctx["raw"])
        elif action == "terminal":
            cpu = self.cpus[ctx["target"]]
            msg = codec.unpack_record("event_message", bytes.fromhex(pending["payload"]["hex"]))
            credit = self.credits[ctx["token"]]
            need(credit["block"] == cpu.block and msg["task_sequence"] == cpu.task_sequence
                 and credit["sequence"] == cpu.task_sequence, "terminal identity/credit")
            credit["result"] = msg
            if ctx["instruction"] is not None:
                self._commit(cpu, ctx["instruction"], ctx["raw"])
            cpu.active = False
            cpu.holding = False
        elif action == "native_cmd":
            op = self.operations[ctx["operation"]]
            wire = pending["payload"]
            need(wire["cmd_op"] == 6 and wire["cmd_index"] == 0 and wire["cmd_data"] == 0,
                 "M fixture supports clear-valid only")
            # Small native behavior peer: clear-valid, preserve scale. No GEMM implementation.
            state = self.native_state[op["block"]]
            for field in ["a_valid", "b_valid", "merged_valid", "partial_valid"]:
                state[field] = False
            self.native[op["id"]] = dict(due=self.tick+self.latency("native"), operation=op["id"])
        elif action == "native_rsp":
            op = self.operations[ctx["operation"]]
            op["done"] = True
            op["error"] = bool(pending["payload"]["rsp_error"])
            del self.native[op["id"]]
        elif action == "data":
            link = self.links[ctx["pair"]]
            h = codec.unpack_record("data_header", bytes.fromhex(pending["payload"]["header_hex"]))
            need(h == link["header"], "DATA identity changed")
            need(len(bytes.fromhex(pending["payload"]["data_hex"])) == h["valid_bytes"], "DATA size")
            rx = self.operations[link["rx"]]
            self._match_rx(h, rx)
            link.update(phase="store", due=self.tick+self.latency("store"))
        elif action == "ack_send":
            link = self.links[ctx["pair"]]
            self._check_ack(link, pending["payload"])
            op = self.operations[link["rx"]]
            op["done"] = True
            self._op_state("finish_rx", op)
            if link["tx"] is None:
                del self.links[ctx["pair"]]
            else:
                link.update(phase="ack_transit", due=self.tick+self.latency("ack"))
        elif action == "ack_recv":
            link = self.links[ctx["pair"]]
            self._check_ack(link, pending["payload"])
            op = self.operations[link["tx"]]
            need(not op["done"], "duplicate TX completion")
            op["done"] = True
            self._op_state("finish_tx", op)
            del self.links[ctx["pair"]]
        else:
            raise ValueError("unknown channel completion")

    def latency(self, name):
        value = self.environment.get("latency", {}).get(name, 2)
        need(type(value) is int and 1 <= value <= 64, "peer latency outside model bound")
        return value

    def _op_state(self, kind, op):
        self._state(kind, op["block"], operation=op["id"], service_sequence=op["sequence"],
                    descriptor=op["descriptor"])

    def _allocate(self, cpu, ins, kind):
        need(not cpu.tokens and ins["b"] not in cpu.tokens, "local token/service occupied")
        seq = cpu.service_sequence
        cpu.service_sequence += 1
        op = dict(id="%d:%d" % (cpu.block, seq), block=cpu.block, sequence=seq,
                  descriptor=ins["c"], token=ins["b"], kind=kind, done=False, retired=False,
                  error=False, issue_pc=cpu.pc)
        cpu.tokens[ins["b"]] = op["id"]
        self.operations[op["id"]] = op
        return op

    def _transfer_header(self, block, desc, tx):
        return codec.unpack_record("data_header", codec.pack_record("data_header",
            dict(kind=0, job_id=self.job, epoch=self.epoch, flags=1,
                 source_block=block if tx else desc["peer_block"],
                 destination_block=desc["peer_block"] if tx else block,
                 source_port=desc["port_id"] if tx else desc["peer_port"],
                 destination_port=desc["peer_port"] if tx else desc["port_id"],
                 source_object=desc["object_id"] if tx else desc["peer_object"],
                 destination_object=desc["peer_object"] if tx else desc["object_id"],
                 edge_id=desc["edge_id"], invocation=desc["invocation"], fragment=desc["fragment"],
                 format=desc["format"], object_version=desc["object_version"], valid_bytes=desc["count_bytes"])))

    def _match_rx(self, header, op):
        need(op["kind"] == "rx" and not op["done"], "RX not armed/already completed")
        need(header == self._transfer_header(op["block"], op["transfer"], False),
             "RX packet identity does not match armed descriptor")

    def _make_link(self, header, data, rx, tx):
        key = route(header)
        need(key not in self.links and len(self.links) < MAX_LINKS, "finite route slot occupied/full")
        self._match_rx(header, rx)
        need(len(data) == header["valid_bytes"] == 16, "RAW16 payload size")
        self.links[key] = dict(header=header, data=bytes(data), rx=rx["id"],
                               tx=tx["id"] if tx else None, phase="data")
        self.peak_links = max(self.peak_links, len(self.links))
        actor = tx["block"] if tx else rx["block"]
        self._offer(key+".data", self._event("data", actor, pair=key),
                    dict(header_hex=codec.pack_record("data_header", header).hex(), data_hex=data.hex()),
                    "data", pair=key)

    def _ack_payload(self, link):
        header = dict(link["header"])
        header.update(kind=1, stored_bytes=len(link["data"]))
        return dict(header_hex=codec.pack_record("data_header", header).hex())

    def _check_ack(self, link, payload):
        need(payload == self._ack_payload(link), "ACK identity/stored byte mismatch")

    def _peers_step(self):
        for key, request in list(self.native.items()):
            channel = "M.%d.response" % self.operations[key]["block"]
            if self.tick >= request["due"] and channel not in self.channels:
                op = self.operations[key]
                self._offer(channel, self._event("native_rsp", op["block"], operation=key,
                            service_sequence=op["sequence"]),
                            dict(rsp_data=0, rsp_error=int(self.environment.get("native_error", False)),
                                 rsp_saturated=0), "native_rsp", operation=key)
        # External packet templates are environment inputs, never read from cases or program tables.
        for i, packet in enumerate(self.environment.get("ingress", [])):
            if i in self.ingress_sent:
                continue
            h = dict(packet["header"])
            h.update(job_id=self.job, epoch=self.epoch)
            h = codec.unpack_record("data_header", codec.pack_record("data_header", h))
            candidates = [o for o in self.operations.values() if o["kind"] == "rx" and not o["done"]
                          and o["block"] == h["destination_block"]
                          and o["transfer"]["edge_id"] == h["edge_id"]]
            if candidates:
                need(len(candidates) == 1, "ambiguous external RX")
                self._make_link(h, bytes.fromhex(packet["data_hex"]), candidates[0], None)
                self.ingress_sent.add(i)
        for key, link in list(self.links.items()):
            if link["phase"] == "store" and self.tick >= link["due"]:
                rx = self.operations[link["rx"]]
                cpu = self.cpus["local"+str(rx["block"])]
                obj = cpu.objects[rx["transfer"]["object_id"]]
                start = obj["descriptor"]["base_bytes"] + rx["transfer"]["offset_bytes"]
                need(start + len(link["data"]) <= len(self.sram[rx["block"]]), "S write range")
                self.sram[rx["block"]][start:start+len(link["data"])] = link["data"]
                obj["valid"] = True
                self._state("store_ack", rx["block"], pair=key, bytes=len(link["data"]))
                link["phase"] = "ack_send"
                self._offer(key+".ack", self._event("ack_send", rx["block"], pair=key),
                            self._ack_payload(link), "ack_send", pair=key)
            elif link["phase"] == "ack_transit" and self.tick >= link["due"]:
                tx = self.operations[link["tx"]]
                link["phase"] = "ack_recv"
                self._offer("source.ack", self._event("ack_recv", tx["block"], pair=key),
                            self._ack_payload(link), "ack_recv", pair=key)

    def _terminal(self, cpu, ins=None, raw=None):
        need(not cpu.tokens and not cpu.objects, "terminal with live local obligations")
        error = cpu.error_pc is not None
        packet = codec.pack_record("event_message", dict(kind=3 if error else 2,
            source_block=cpu.block, job_id=self.job, epoch=self.epoch, task_sequence=cpu.task_sequence,
            completion_token=cpu.completion_token, status=9 if error else 0,
            error_pc=cpu.error_pc if error else 0xffffffff))
        cpu.holding = True
        self._offer("return."+str(cpu.block), self._event("terminal",cpu.block),
                    dict(hex=packet.hex()), "terminal", target=cpu.target,
                    token=cpu.completion_token, instruction=ins, raw=raw)

    def _mother_step(self, cpu, ins, raw):
        op = ins["op"]
        if op == "G_MOVI":
            cpu.regs[ins["a"]] = ins["x"]
            self._commit(cpu, ins, raw)
        elif op == "G_CALL":
            block, token = ins["a"], ins["b"]
            target = self.cpus["local"+str(block)]
            need(token not in self.credits and not target.active and len(self.credits) < 2,
                 "CALL task/return credit unavailable")
            sequence = self.sequence[block]+1
            packet = dict(kind=0, target_block=block, completion_token=token,
                          job_id=self.job, epoch=self.epoch, task_sequence=sequence,
                          task_descriptor=ins["c"], program_image_id=target.header["program_image_id"],
                          topology_id=target.header["topology_id"])
            packet.update({"arg%d"%i: cpu.regs[i] for i in range(8)})
            self.credits[token] = dict(block=block, sequence=sequence, result=None)
            target.task_sequence = sequence  # reserved identity, not task admission
            self._state("reserve", block)
            cpu.holding = True
            self._offer("mother.call", self._event("call",block),
                        dict(hex=codec.pack_record("task_message",packet).hex()), "call",
                        block=block, instruction=ins, raw=raw)
        elif op == "G_EVENT":
            bindings = [cpu.record("event_binding",i) for i in range(cpu.header["event_binding_count"])]
            binding = next((b for b in bindings if b["event_id"] == ins["b"]), None)
            need(binding is not None, "G_EVENT binding missing")
            if self.ready_event is None:
                return
            e = self.ready_event
            source = self.cpus["local"+str(binding["source_block"])]
            need(e["source_block"] == binding["source_block"] and e["kind"] == binding["message_kind"]
                 and e["event_id"] == ins["b"] and e["job_id"] == self.job and e["epoch"] == self.epoch
                 and e["task_sequence"] == source.task_sequence and e["event_sequence"] == 1,
                 "G_EVENT stale/wrong producer")
            cpu.regs[ins["a"]] = e["scalar"]
            self._state("consume_ready",source.block)
            self.ready_event = None
            self._commit(cpu,ins,raw)
        elif op == "G_WAIT":
            tokens = [i for i in range(32) if ins["x"] & (1 << i)]
            need(all(i in self.credits for i in tokens), "G_WAIT unallocated token")
            if not all(self.credits[i]["result"] is not None for i in tokens):
                return
            failed = False
            for token in tokens:
                credit = self.credits.pop(token)
                failed |= credit["result"]["status"] != 0
                self._state("consume_done", credit["block"])
            self._commit(cpu,ins,raw)
            if failed:
                need(not self.credits and self._idle(), "fault requires wider coordinated drain")
                self._state("global_error")
                self.outcome = "error"
                cpu.active = False
        elif op == "G_END":
            need(not self.credits and self.ready_event is None and self._idle(), "G_END obligations remain")
            self._commit(cpu,ins,raw)
            self._state("global_end")
            self.outcome = "success"
            cpu.active = False
        else:
            raise ValueError("mother instruction outside execution profile")

    def _local_step(self, cpu, ins, raw):
        op = ins["op"]
        if op == "L_MOVI":
            cpu.regs[ins["a"]] = ins["x"]
        elif op == "L_OPEN":
            obj = cpu.record("object",ins["a"])
            need(ins["a"] not in cpu.objects and not cpu.objects, "finite object reservation busy")
            cpu.objects[ins["a"]] = dict(descriptor=obj, valid=False)
            self._state("open",cpu.block,object=ins["a"])
        elif op == "L_EXEC":
            e = cpu.record("execution",ins["c"])
            need(e["resource"] == ins["a"] == 0 and e["native_op"] == 6 and e["service"] == 0,
                 "EXEC profile/service")
            operation = self._allocate(cpu,ins,"exec")
            self._op_state("exec",operation)
            self._offer("M.%d.command"%cpu.block,
                        self._event("native_cmd",cpu.block,operation=operation["id"],
                                    service_sequence=operation["sequence"]),
                        dict(cmd_op=e["native_op"], cmd_index=e["native0"],
                             cmd_data=e["native1"] | (e["native2"] << 32)), "native_cmd",
                        operation=operation["id"])
        elif op in ("L_RX","L_TX"):
            desc = cpu.record("transfer",ins["c"])
            tx = op == "L_TX"
            need(desc["direction"] == tx and desc["object_id"] in cpu.objects, "transfer object/direction")
            obj = cpu.objects[desc["object_id"]]
            need(not tx or obj["valid"], "TX object is invalid")
            operation = self._allocate(cpu,ins,"tx" if tx else "rx")
            operation["transfer"] = desc
            self._op_state("arm_tx" if tx else "arm_rx",operation)
            if tx:
                header = self._transfer_header(cpu.block,desc,True)
                candidates = [o for o in self.operations.values() if o["kind"] == "rx" and not o["done"]
                              and o["block"] == desc["peer_block"] and o["transfer"]["edge_id"] == desc["edge_id"]]
                need(len(candidates) == 1, "TX requires prepared finite receiver")
                start = obj["descriptor"]["base_bytes"] + desc["offset_bytes"]
                data = bytes(self.sram[cpu.block][start:start+desc["count_bytes"]])
                self._make_link(header,data,candidates[0],operation)
        elif op == "L_WAIT":
            tokens = [i for i in range(8) if ins["x"] & (1 << i)]
            need(all(i in cpu.tokens for i in tokens), "L_WAIT unallocated token")
            if not all(self.operations[cpu.tokens[i]]["done"] for i in tokens):
                return
            for token in tokens:
                operation = self.operations[cpu.tokens.pop(token)]
                operation["retired"] = True
                self._op_state("wait",operation)
                if operation["error"]:
                    cpu.error_pc = operation["issue_pc"]
            self._commit(cpu,ins,raw)
            if cpu.error_pc is not None:
                self._terminal(cpu)
            return
        elif op == "L_REPORT":
            need(ins["c"] == 0 and any(self.operations[v]["kind"] == "rx" for v in cpu.tokens.values()),
                 "READY requires armed receiver")
            cpu.event_sequence += 1
            packet = codec.pack_record("event_message",dict(kind=ins["c"],source_block=cpu.block,
                job_id=self.job,epoch=self.epoch,task_sequence=cpu.task_sequence,event_id=ins["a"],
                scalar=cpu.regs[ins["b"]],event_sequence=cpu.event_sequence))
            cpu.holding = True
            self._offer("return."+str(cpu.block),self._event("ready",cpu.block),dict(hex=packet.hex()),
                        "ready",target=cpu.target,instruction=ins,raw=raw)
            return
        elif op == "L_DROP":
            need(ins["a"] in cpu.objects and not any(
                not o["retired"] and o["block"] == cpu.block and
                o.get("transfer",{}).get("object_id") == ins["a"] for o in self.operations.values()),
                "DROP with outstanding object obligation")
            del cpu.objects[ins["a"]]
            self._state("drop",cpu.block,object=ins["a"])
        elif op == "L_END":
            self._terminal(cpu,ins,raw)
            return
        else:
            raise ValueError("local instruction outside execution profile")
        self._commit(cpu,ins,raw)

    def _idle(self):
        return (not self.channels and not self.links and not self.native
                and not any(c.active or c.tokens or c.objects for k,c in self.cpus.items() if k != "mother")
                and all(o["retired"] for o in self.operations.values()))

    def activity(self):
        locals_ = [c for k,c in self.cpus.items() if k != "mother"]
        return dict(tasks=sum(int(c.active) for c in locals_), data=len(self.links),
                    returns=len(self.channels)+int(self.ready_event is not None)+len(self.credits),
                    contexts=sum(len(c.tokens)+len(c.objects) for c in locals_), untagged=len(self.native))

    def run(self, job=7, epoch=1, max_ticks=256):
        need(type(job) is int and 0 < job < 1 << 32 and type(epoch) is int and 0 < epoch < 1 << 32,
             "job/epoch identity")
        need(type(max_ticks) is int and 1 <= max_ticks <= 1024, "tick experiment bound")
        need(self.loader.expected_digest == self.manifest_sha256 and self.loader._images() == self.images,
             "execution instance image changed; create new Machine after reload")
        self.loader.start(self.loader.expected_digest)
        self.last_report = None
        self.job,self.epoch = job,epoch
        self.tick = 0
        self.rng = random.Random(self.environment.get("seed",0))
        self.cpus = {k:CPU(k,data) for k,data in self.images.items()}
        self.events,self.retired = [],[]
        self.channels,self.links,self.native,self.operations,self.credits = {},{},{},{},{}
        self.ready_event = None
        self.ingress_sent = set()
        self.peak_channels,self.peak_links = 0,0
        self.outcome = None
        try:
            for self.tick in range(max_ticks):
                self._channels_step()
                self._peers_step()
                order = ["mother"] + self.environment.get("local_order",sorted(k for k in self.cpus if k != "mother"))
                need(set(order) == set(self.cpus) and len(order) == len(self.cpus), "CPU scheduler order")
                for key in order:
                    cpu = self.cpus[key]
                    if not cpu.active or cpu.holding:
                        continue
                    ins, raw = cpu.fetch()
                    if cpu.role == "mother":
                        self._mother_step(cpu,ins,raw)
                    else:
                        self._local_step(cpu,ins,raw)
                self.loader.observe_activity(**self.activity())
                if self.outcome is not None:
                    need(self._idle() and not self.credits and self.ready_event is None, "job terminal not drained")
                    self.loader.quiesce()
                    self.loader.drained()
                    self.jobs_completed += 1
                    self.last_report = dict(schema="binary-control-run/0.1",bundle=self.loader.manifest["bundle"],
                        manifest_sha256=self.loader.expected_digest,job=job,epoch=epoch,
                        outcome=self.outcome,instructions_executed=True,rtl_tested=False,
                        actual_storage="finite Python bytearrays, not S RTL",
                        ticks=self.tick+1,ticks_are_hardware_cycles=False,
                        events=self.events,retired=self.retired,
                        cpu={k:dict(pc=c.pc,steps=c.steps,fetch_reads=c.reads,registers=c.regs,
                                    arguments=c.arguments,task_sequence=c.task_sequence)
                             for k,c in self.cpus.items()},
                        final_activity=self.activity(),peak_channels=self.peak_channels,peak_links=self.peak_links,
                        sram_sha256={str(k):image.digest(bytes(v)) for k,v in self.sram.items()},
                        native_state={str(k):copy.deepcopy(v) for k,v in self.native_state.items()},
                        loader_state=self.loader.state)
                    return copy.deepcopy(self.last_report)
            raise ModelBound("execution tick bound reached; no architectural terminal result")
        except Exception as error:
            self.last_failure = dict(kind=type(error).__name__,message=str(error),tick=self.tick,
                                     activity=self.activity(),architectural_terminal=False)
            self.loader.reset()  # failed experiment cannot leave the cohort admitted
            raise
