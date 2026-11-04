"""Boundary property checker. Observations are inputs; no DUT outputs are generated."""
import pathlib
import sys
import generate
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"control_image_v0_1"))
import image
codec = image.codec
C = generate.contract()
PINS = {p["name"]:p for g in C["groups"] for p in g["pins"]}
LIFE = C["lifecycle"]


def need(value,message):
    if not value:
        raise ValueError(message)


def number(value):
    if isinstance(value,str):
        return int(value,16) if value.startswith("0x") else int(value)
    need(type(value) is int,"signal must be integer/hex")
    return value


def sample(values):
    need(not set(values)-set(PINS),"unknown pin")
    row = {k:0 for k in PINS}
    row["rst_ni"] = 1
    for name,value in values.items():
        row[name] = number(value)
        need(0 <= row[name] < 1 << PINS[name]["width"],"pin width: "+name)
    return row


class Checker:
    def __init__(self):
        self.shadow = bytearray([0xcd]*8320)
        self.release_seq,self.generation = 0,0
        self.reset()

    def reset(self):
        self.authorized,self.checked,self.prepared,self.poisoned = False,False,False,False
        self.held = {}
        self.cfg,self.pm,self.ireg,self.task,self.service = None,None,None,None,None
        self.written,self.read,self.total,self.next_service = 0,0,0,0
        self.header = None
        self.prior_life = "RESET_WAIT"
        self.cancelled = False
        self.close_request = None

    def check(self,trace,complete=True):
        need(trace["schema"] == "local-boundary-cycles/0.1" and len(trace["cycles"]) <= 8192,"trace schema/bound")
        for t,row in enumerate(trace["cycles"]):
            need(row["cycle"] == t,"contiguous cycles")
            self.cycle(t,sample(row["signals"]))
        if complete:
            need(not self.held and all(x is None for x in [self.cfg,self.pm,self.ireg,self.task,self.service]),
                 "unclosed boundary obligation")
        return dict(boundary_valid=True,cycles=len(trace["cycles"]),rtl_tested=False,
                    evidence=trace.get("evidence"),full_controller_semantics=False)

    def cycle(self,t,s):
        if not s["rst_ni"]:
            need(not any(s[k] for k in ["pm_req_valid_o","svc_req_valid_o","event_valid_o",
                                        "cfg_rsp_valid_o","task_ready_o","image_valid_o"]),"reset valid/admission")
            self.reset()
            return
        inv = {v:k for k,v in LIFE.items()}
        need(s["life_o"] in inv and s["seq_o"] in C["sequencer"].values(),"state code")
        life = inv[s["life_o"]]
        if life != self.prior_life:
            need(life in C["transition_edges"][self.prior_life],"lifecycle transition")
        self.prior_life = life
        prior_held = dict(self.held)
        for ch in C["channels"]:
            v,r = s[ch["valid"]],s[ch["ready"]]
            value = tuple(s[k] for k in ch["payload"])
            if ch["name"] in self.held:
                need(v and value == self.held[ch["name"]],"held tuple changed/dropped: "+ch["name"])
            if v and not r:
                self.held[ch["name"]] = value
            else:
                self.held.pop(ch["name"],None)
        need(life == "RESET_WAIT" or self.authorized,"cohort release missing")
        if life == "POISONED":
            self.poisoned = True
        need(not self.poisoned or s["poison_o"],"poison not sticky")
        valid = self.authorized and self.prepared and not self.poisoned and s["deploy_valid_i"] and \
                s["deploy_generation_i"] == self.generation
        need(s["image_valid_o"] == int(valid),"cohort/image gate")
        need(s["trace_ireg_valid_o"] == int(self.ireg is not None),"IREG visibility")
        if life in ("RUNNING","CANCELLING"):
            need(self.task is not None and valid and not s["cfg_req_ready_o"],"running/config write interlock")
        if life == "READY":
            need(self.task is None and valid,"READY before task/cohort completion")
        if self.cfg is not None:
            need(not s["cfg_req_ready_o"],"configuration single outstanding/bubble")
        if s["cfg_req_valid_i"] and s["cfg_req_op_i"] == 0 and life in ("READY","INVALID") and self.cfg is None:
            need(not s["task_ready_o"],"BEGIN priority over CALL")
        fire = lambda v,r: bool(s[v] and s[r])
        cfg = fire("cfg_req_valid_i","cfg_req_ready_o")
        mem = fire("pm_req_valid_o","pm_req_ready_i")
        mrsp = fire("pm_rsp_valid_i","pm_rsp_ready_o")
        task = fire("task_valid_i","task_ready_o")
        svc = fire("svc_req_valid_o","svc_req_ready_i")
        srsp = fire("svc_rsp_valid_i","svc_rsp_ready_o")
        evt = fire("event_valid_o","event_ready_i")
        old_cfg,old_pm,old_svc = self.cfg,self.pm,self.service
        if mem:
            need(old_pm is None and not mrsp,"program memory single outstanding/no refill")
        if mrsp:
            need(old_pm is not None and t > old_pm["cycle"],"memory response before accepted request")
        if svc:
            need(old_svc is None and not srsp,"service single outstanding/no refill")
        if srsp:
            need(old_svc is not None and old_svc["done"] is None and t > old_svc["cycle"],
                 "service response before command/duplicate")
        if fire("release_valid_i","release_ready_o"):
            need(life == "RESET_WAIT" and s["release_sequence_i"] > self.release_seq and s["release_epoch_i"] > 0,
                 "stale release")
            self.authorized = True
            self.release_seq,self.cert_epoch = s["release_sequence_i"],s["release_epoch_i"]
        if cfg:
            need(old_cfg is None and not task and life not in ("RUNNING","CANCELLING","POISONED","RESET_WAIT"),
                 "configuration ownership")
            op = s["cfg_req_op_i"]
            need(op in range(6),"reserved configuration opcode")
            if op == 0:
                need(life in ("INVALID","READY") and self.task is None and old_pm is None and
                     144 <= s["cfg_req_total_bytes_i"] <= 8320 and s["cfg_req_total_bytes_i"]%16 == 0 and
                     s["cfg_req_generation_i"] > self.generation,"BEGIN metadata/idle")
                self.generation,self.total = s["cfg_req_generation_i"],s["cfg_req_total_bytes_i"]
                self.written,self.read,self.checked,self.prepared = 0,0,False,False
                self.ids = [s[k] for k in ["cfg_req_image_id_i","cfg_req_topology_id_i",
                                           "cfg_req_abi_id_i","cfg_req_capacity_id_i"]]
            else:
                need(s["cfg_req_generation_i"] == self.generation,"configuration generation")
                if op in (1,2):
                    need(life == "LOADING" and s["cfg_req_address_i"]%16 == 0 and
                         s["cfg_req_address_i"]+16 <= self.total,"configuration range")
                    need(s["cfg_req_address_i"] == (self.written if op == 1 else self.read),"contiguous prefix")
                    need(op != 2 or self.written == self.total,"readback before write ACKs")
                elif op == 3:
                    need(s["cfg_req_proof_i"] and self.written == self.read == self.total,
                         "verification before full actual readback")
                    h = image.parse_image(bytes(self.shadow[:self.total]),"local")["header"]
                    need([h[k] for k in ["program_image_id","topology_id","native_abi_id","capacity_profile_id"]]
                         == self.ids,"image header identity")
                    self.header,self.checked = h,True
                elif op == 4:
                    need(life == "VERIFIED" and self.checked,"PREPARE before verified")
                    self.prepared = True
                elif op == 5:
                    self.checked,self.prepared = False,False
            self.cfg = dict(op=op,cycle=t,address=s["cfg_req_address_i"],data=s["cfg_req_data_i"],
                            mem_seen=False,mem_done=False,read_data=0)
        if s["cfg_rsp_valid_o"]:
            need(old_cfg is not None and t > old_cfg["cycle"],"configuration response without request")
            need(old_cfg["op"] not in (1,2) or old_cfg["mem_done"],"configuration response before stored ACK")
            need(s["cfg_rsp_status_o"] == 0 and s["cfg_rsp_generation_o"] == self.generation and
                 s["cfg_rsp_data_o"] == old_cfg["read_data"],"nominal cfg response/payload")
            if s["cfg_rsp_ready_i"]:
                if old_cfg["op"] == 2:
                    self.read += 16
                self.cfg = None
        if mem:
            owner,address = s["trace_pm_owner_o"],s["pm_req_address_o"]
            need(owner in (0,1,2) and address%16 == 0 and address+16 <= self.total,"memory address/owner")
            if owner == 0:
                need(old_cfg is not None and old_cfg["op"] in (1,2) and t > old_cfg["cycle"] and
                     not old_cfg["mem_seen"] and life == "LOADING","configuration memory owner")
                need(address == old_cfg["address"] and s["pm_req_write_o"] == (old_cfg["op"] == 1) and
                     (not s["pm_req_write_o"] or s["pm_req_data_o"] == old_cfg["data"]),"write/read tuple")
                old_cfg["mem_seen"] = True
            else:
                need(not s["pm_req_write_o"] and self.task is not None and
                     (life == "RUNNING" or life == "CANCELLING" and "pm_req" in prior_held),
                     "fetch/load port ownership")
                if owner == 1:
                    need(self.ireg is None and s["trace_pc_o"] < self.header["instruction_count"] and
                         address == self.header["instruction_offset"]+16*s["trace_pc_o"],"fetch PC/address/prefetch")
            self.pm = dict(owner=owner,address=address,write=s["pm_req_write_o"],data=s["pm_req_data_o"],
                           pc=s["trace_pc_o"],cycle=t)
        if mrsp:
            need(not s["pm_rsp_error_i"],"nominal memory error")
            a = old_pm["address"]
            if old_pm["write"]:
                self.shadow[a:a+16] = old_pm["data"].to_bytes(16,"little")
                self.written += 16
            else:
                need(s["pm_rsp_data_i"] == int.from_bytes(self.shadow[a:a+16],"little"),"memory payload")
            if old_pm["owner"] == 0:
                need(old_cfg is not None,"config owner lost")
                old_cfg.update(mem_done=True,read_data=s["pm_rsp_data_i"] if old_cfg["op"] == 2 else 0)
            elif old_pm["owner"] == 1:
                need(self.ireg is None,"IREG overwritten")
                self.ireg = dict(word=s["pm_rsp_data_i"],pc=old_pm["pc"],cycle=t)
            self.pm = None
        if task:
            m = codec.unpack_record("task_message",s["task_packet_i"].to_bytes(64,"little"))
            if m["kind"] == 0:
                need(life == "READY" and self.task is None and s["task_credit_i"] and valid and
                     self.cfg is None and self.pm is None,"CALL without credit/image/capacity")
                need(m["target_block"] == trace_block(self) and m["epoch"] >= self.cert_epoch and
                     m["program_image_id"] == self.header["program_image_id"] and
                     m["topology_id"] == self.header["topology_id"],"CALL identity")
                self.task,self.next_service,self.task_error = m,0,0
            else:
                need(self.task is not None and all(m[k] == self.task[k] for k in
                     ["job_id","epoch","task_sequence","target_block","completion_token"]),"CANCEL identity")
                self.cancelled = True
        if svc:
            need(self.ireg is not None and t > self.ireg["cycle"] and
                 (life == "RUNNING" or life == "CANCELLING" and "svc_req" in prior_held),
                 "issue without instruction/new issue after cancel")
            ins = codec.decode_instruction(self.ireg["word"],"local")
            kind = {"L_EXEC":0,"L_RX":1,"L_TX":2}.get(ins["op"])
            need(kind is not None and s["svc_req_kind_o"] == kind and s["svc_req_token_o"] == ins["b"] and
                 s["svc_req_sequence_o"] == self.next_service,"service opcode/token/sequence")
            for pin,key in [("svc_req_job_o","job_id"),("svc_req_epoch_o","epoch"),
                            ("svc_req_task_sequence_o","task_sequence")]:
                need(s[pin] == self.task[key],"service identity snapshot")
            name,size = ("execution",128) if kind == 0 else ("transfer",64)
            need(ins["c"] < self.header[name+"_count"],"descriptor index")
            a = self.header[name+"_offset"]+ins["c"]*size
            need(s["svc_req_descriptor_o"] == int.from_bytes(self.shadow[a:a+size],"little"),"descriptor snapshot")
            if kind == 0:
                need(s["svc_req_resource_o"] == ins["a"] and not any(s[k] for k in
                     ["svc_req_object_base_o","svc_req_object_length_o","svc_req_object_version_o"]),
                     "EXEC resource/object snapshot")
            else:
                descriptor = codec.unpack_record("transfer",bytes(self.shadow[a:a+size]))
                oa = self.header["object_offset"]+descriptor["object_id"]*64
                obj = codec.unpack_record("object",bytes(self.shadow[oa:oa+64]))
                need(s["svc_req_resource_o"] == 5 and s["svc_req_object_base_o"] == obj["base_bytes"] and
                     s["svc_req_object_length_o"] == obj["length_bytes"] and
                     s["svc_req_object_version_o"] == obj["object_version"],"object window snapshot")
            self.service = dict(kind=kind,token=ins["b"],seq=self.next_service,cycle=t,done=None)
            self.next_service += 1
        if srsp:
            need(s["svc_rsp_kind_i"] == old_svc["kind"] and s["svc_rsp_token_i"] == old_svc["token"] and
                 s["svc_rsp_sequence_i"] == old_svc["seq"],"response association")
            for pin,key in [("svc_rsp_job_i","job_id"),("svc_rsp_epoch_i","epoch"),
                            ("svc_rsp_task_sequence_i","task_sequence")]:
                need(s[pin] == self.task[key],"stale service response")
            old_svc["done"] = t
            if s["svc_rsp_status_i"]:
                self.task_error = s["svc_rsp_status_i"]
        close_req = fire("close_req_valid_o","close_req_ready_i")
        close_rsp = fire("close_rsp_valid_i","close_rsp_ready_o")
        if close_req:
            need(life == "CANCELLING" and old_svc is not None and old_svc["kind"] == 1 and
                 old_svc["done"] is None and self.close_request is None,"RX close ownership")
            need(s["close_req_sequence_o"] == old_svc["seq"] and s["close_req_token_o"] == old_svc["token"] and
                 all(s[pin] == self.task[key] for pin,key in [("close_req_job_o","job_id"),
                     ("close_req_epoch_o","epoch"),("close_req_task_sequence_o","task_sequence")]),"RX close identity")
            self.close_request = dict(cycle=t,seq=old_svc["seq"],token=old_svc["token"])
        if close_rsp:
            need(not srsp and self.close_request is not None and t > self.close_request["cycle"] and
                 old_svc is not None and old_svc["done"] is None and
                 s["close_rsp_sequence_i"] == old_svc["seq"] and s["close_rsp_token_i"] == old_svc["token"] and
                 s["close_rsp_status_i"] == 0 and all(s[pin] == self.task[key] for pin,key in
                     [("close_rsp_job_i","job_id"),("close_rsp_epoch_i","epoch"),
                      ("close_rsp_task_sequence_i","task_sequence")]),"RX close ACK before barrier/wrong identity")
            old_svc["done"] = t
            self.close_request = None
        if s["trace_cancel_token_retire_o"]:
            need(life == "CANCELLING" and old_svc is not None and old_svc["done"] is not None and
                 old_svc["done"] < t and not s["trace_retire_o"],"cancel cleanup before completion")
            self.service = None
        if s["trace_cancel_object_drop_o"]:
            need(life == "CANCELLING" and self.service is None,"cancel object release with outstanding service")
        if s["trace_retire_o"]:
            need(self.ireg is not None and t > self.ireg["cycle"] and self.task is not None and not self.poisoned,
                 "retire before instruction response")
            if life == "CANCELLING":
                need(svc and "svc_req" in prior_held or evt and "event" in prior_held,
                     "new instruction retirement after cancel")
            ins = codec.decode_instruction(self.ireg["word"],"local")
            need(s["trace_pc_o"] == self.ireg["pc"] and s["trace_opcode_o"] == self.ireg["word"] >> 120,
                 "retiring PC/opcode")
            if ins["op"] in ("L_EXEC","L_RX","L_TX"):
                need(svc,"retire before adapter acceptance")
            elif ins["op"] == "L_WAIT":
                need(old_svc is not None and old_svc["done"] is not None and old_svc["done"] < t and
                     ins["x"] == 1 << old_svc["token"],"WAIT before prior-cycle completion")
                self.service = None
            elif ins["op"] in ("L_REPORT","L_END"):
                need(evt,"retire before whole packet acceptance")
            self.ireg = None
        if evt:
            m = codec.unpack_record("event_message",s["event_packet_o"].to_bytes(64,"little"))
            need(self.task is not None and m["source_block"] == trace_block(self) and
                 all(m[k] == self.task[k] for k in ["job_id","epoch","task_sequence"]),"return identity")
            if m["kind"] in (2,3):
                need(m["completion_token"] == self.task["completion_token"] and self.service is None and
                     self.pm is None,"terminal service/credit obligation")
                need(not self.task_error or m["kind"] == 3 and m["status"] == self.task_error,
                     "success hides service error")
                if self.cancelled and m["status"] == 11:
                    self.ireg = None
                self.task = None
        if life == "CANCELLING":
            need(self.cancelled,"cancel state without accepted CANCEL")


def trace_block(checker):
    return getattr(checker,"block",0)


def check_trace(trace,complete=True):
    checker = Checker()
    checker.block = trace.get("block",0)
    return checker.check(trace,complete)


def check_flits(packet,cycles):
    need(isinstance(packet,bytes) and len(packet) == 64,"packet length")
    index,held = 0,None
    for row in cycles:
        valid,ready,data = row["valid"],row["ready"],number(row["data"])
        need(valid in (0,1) and ready in (0,1) and 0 <= data < 1 << 32,"flit width")
        if held is not None:
            need(valid and data == held,"held flit changed/dropped")
        need(row.get("packet_accepted",False) == bool(valid and ready and index == 15),"packet accept before last flit")
        if valid:
            need(index < 16 and data == int.from_bytes(packet[4*index:4*index+4],"little"),"flit order")
            if ready:
                index += 1
                held = None
            else:
                held = data
    need(index == 16 and held is None,"partial packet")
    return dict(flits=16,packet_accepted=True,rtl_tested=False)
