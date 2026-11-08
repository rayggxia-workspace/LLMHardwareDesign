"""Authored expected boundary schedules, not a DUT or a controller simulator."""
import argparse
import copy
import json
import pathlib
import check_cycles
import generate

HERE = pathlib.Path(__file__).resolve().parent
C = generate.contract()
codec = check_cycles.codec


class Schedule:
    def __init__(self,data):
        self.data = data
        self.header = codec.unpack_record("image_header",data[:128])
        self.life,self.seq = "RESET_WAIT","IDLE"
        self.ireg,self.pc,self.deployed = 0,0,0
        self.rows = []

    def add(self,**signals):
        base = dict(life_o=C["lifecycle"][self.life],seq_o=C["sequencer"][self.seq],
                    trace_ireg_valid_o=self.ireg,trace_pc_o=self.pc,image_valid_o=self.deployed,
                    deploy_valid_i=self.deployed,deploy_generation_i=1 if self.deployed else 0)
        base.update(signals)
        # Wide bus payloads use hex strings to avoid JSON-number precision loss.
        for name in list(base):
            if check_cycles.PINS[name]["width"] > 32:
                base[name] = hex(base[name])
        self.rows.append(dict(cycle=len(self.rows),signals=base))

    def cfg(self,op,address=0,data=0,stall=0):
        fields = dict(cfg_req_valid_i=1,cfg_req_ready_o=1,cfg_req_op_i=op,
                      cfg_req_generation_i=1,cfg_req_address_i=address,cfg_req_data_i=data)
        if op == 0:
            fields.update(cfg_req_total_bytes_i=len(self.data),
                cfg_req_image_id_i=self.header["program_image_id"],cfg_req_topology_id_i=self.header["topology_id"],
                cfg_req_abi_id_i=self.header["native_abi_id"],cfg_req_capacity_id_i=self.header["capacity_profile_id"])
        if op == 3:
            fields["cfg_req_proof_i"] = 1
        self.add(**fields)
        if op == 0:
            self.life = "LOADING"
        elif op == 3:
            self.life = "VERIFIED"
        elif op == 4:
            self.life = "PREPARED"
        if op in (1,2):
            self.add(pm_req_valid_o=1,pm_req_ready_i=1,pm_req_write_o=int(op==1),
                     pm_req_address_o=address,pm_req_data_o=data,trace_pm_owner_o=0)
            self.add(pm_rsp_valid_i=1,pm_rsp_ready_o=1,
                     pm_rsp_data_i=0 if op == 1 else int.from_bytes(self.data[address:address+16],"little"))
        response = dict(cfg_rsp_valid_o=1,cfg_rsp_generation_o=1,
                        cfg_rsp_data_o=int.from_bytes(self.data[address:address+16],"little") if op == 2 else 0)
        for _ in range(stall):
            self.add(cfg_rsp_ready_i=0,**response)
        self.add(cfg_rsp_ready_i=1,**response)

    def load(self,stall=0):
        self.add(rst_ni=0)
        self.add(release_valid_i=1,release_ready_o=1,release_sequence_i=1,release_epoch_i=1)
        self.life = "INVALID"
        self.cfg(0)
        for address in range(0,len(self.data),16):
            self.cfg(1,address,int.from_bytes(self.data[address:address+16],"little"),stall)
        for address in range(0,len(self.data),16):
            self.cfg(2,address,stall=stall)
        self.cfg(3)
        self.cfg(4)
        # PREPARED is observable before deployment grants any admission.
        self.add()
        self.deployed = 1
        self.add()
        self.life = "READY"
        self.add()

    def call(self):
        packet = codec.pack_record("task_message",dict(kind=0,target_block=0,job_id=7,epoch=1,
            task_sequence=1,completion_token=0,task_descriptor=0,
            program_image_id=self.header["program_image_id"],topology_id=self.header["topology_id"]))
        self.add(task_valid_i=1,task_ready_o=1,task_credit_i=1,
                 task_packet_i=int.from_bytes(packet,"little"))
        self.life = "RUNNING"
        self.read_table(self.header["task_offset"],64,"TASK_REQ","TASK_WAIT")

    def read_table(self,start,length,req="DESC_REQ",wait="DESC_WAIT"):
        for address in range(start,start+length,16):
            self.seq = req
            self.add(pm_req_valid_o=1,pm_req_ready_i=1,pm_req_address_o=address,trace_pm_owner_o=2)
            self.seq = wait
            self.add(pm_rsp_valid_i=1,pm_rsp_ready_o=1,
                     pm_rsp_data_i=int.from_bytes(self.data[address:address+16],"little"))

    def fetch(self,pc):
        self.pc = pc
        address = self.header["instruction_offset"]+16*pc
        self.seq = "FETCH_REQ"
        self.add(pm_req_valid_o=1,pm_req_ready_i=1,pm_req_address_o=address,trace_pm_owner_o=1)
        self.seq = "FETCH_WAIT"
        self.add(pm_rsp_valid_i=1,pm_rsp_ready_o=1,
                 pm_rsp_data_i=int.from_bytes(self.data[address:address+16],"little"))
        self.ireg = 1
        self.seq = "DECODE"
        self.add()

    def clear_service(self,stall=2):
        start = self.header["execution_offset"]
        self.read_table(start,128)
        self.seq = "ISSUE"
        fields = dict(svc_req_valid_o=1,svc_req_kind_o=0,svc_req_resource_o=0,svc_req_token_o=0,
            svc_req_sequence_o=0,svc_req_job_o=7,svc_req_epoch_o=1,svc_req_task_sequence_o=1,
            svc_req_descriptor_o=int.from_bytes(self.data[start:start+128],"little"))
        for _ in range(stall):
            self.add(svc_req_ready_i=0,**fields)
        self.add(svc_req_ready_i=1,trace_retire_o=1,trace_opcode_o=0x41,**fields)
        self.ireg = 0
        self.fetch(1)
        self.seq = "WAIT"
        response = dict(svc_rsp_valid_i=1,svc_rsp_kind_i=0,svc_rsp_token_i=0,svc_rsp_sequence_i=0,
                        svc_rsp_job_i=7,svc_rsp_epoch_i=1,svc_rsp_task_sequence_i=1,svc_rsp_status_i=0)
        for _ in range(stall):
            self.add(svc_rsp_ready_o=0,**response)
        self.add(svc_rsp_ready_o=1,**response)
        # Completion is visible to WAIT only in the following cycle.
        self.add(trace_retire_o=1,trace_opcode_o=0x44)
        self.ireg = 0

    def end(self,pc,stall=2):
        self.fetch(pc)
        self.seq = "END_HOLD"
        packet = codec.pack_record("event_message",dict(kind=2,source_block=0,job_id=7,epoch=1,
            task_sequence=1,completion_token=0,status=0))
        signals = dict(event_valid_o=1,event_packet_o=int.from_bytes(packet,"little"))
        for _ in range(stall):
            self.add(event_ready_i=0,**signals)
        self.add(event_ready_i=1,trace_retire_o=1,trace_opcode_o=0x4f,**signals)
        self.ireg = 0
        self.pc = pc+1
        self.life,self.seq = "READY","IDLE"
        self.add()

    def result(self,name):
        return dict(schema="local-boundary-cycles/0.1",name=name,block=0,
                    evidence="authored_expected",rtl_tested=False,cycles=copy.deepcopy(self.rows))


def build():
    bundles = json.loads((HERE.parent/"control_image_v0_1/bundles.json").read_bytes().decode("utf-8"))["bundles"]
    empty = bytes.fromhex(bundles[0]["images_hex"]["local0"])
    single = bytes.fromhex(bundles[1]["images_hex"]["local0"])
    transfer = bytes.fromhex(bundles[2]["images_hex"]["local0"])
    a = Schedule(empty); a.load(); a.call(); a.end(0,0)
    b = Schedule(single); b.load(1); b.call(); b.fetch(0); b.clear_service(2); b.end(2,2)
    c = Schedule(empty); c.load()
    d = Schedule(transfer); d.load(); d.call(); d.fetch(0)
    d.read_table(d.header["object_offset"],64)
    d.add(trace_retire_o=1,trace_opcode_o=0x40); d.ireg = 0
    d.fetch(1); d.read_table(d.header["transfer_offset"],64); d.seq = "ISSUE"
    start = d.header["transfer_offset"]
    d.add(svc_req_valid_o=1,svc_req_ready_i=1,svc_req_kind_o=1,svc_req_resource_o=5,
          svc_req_token_o=0,svc_req_sequence_o=0,svc_req_job_o=7,svc_req_epoch_o=1,
          svc_req_task_sequence_o=1,svc_req_descriptor_o=int.from_bytes(transfer[start:start+64],"little"),
          svc_req_object_base_o=0,svc_req_object_length_o=16,svc_req_object_version_o=1,
          trace_retire_o=1,trace_opcode_o=0x42)
    d.ireg = 0; d.pc = 2; d.seq = "WAIT"
    cancel = codec.pack_record("task_message",dict(kind=1,target_block=0,job_id=7,epoch=1,
        task_sequence=1,completion_token=0,program_image_id=d.header["program_image_id"],
        topology_id=d.header["topology_id"]))
    d.add(task_valid_i=1,task_ready_o=1,task_packet_i=int.from_bytes(cancel,"little"))
    d.life = "CANCELLING"
    d.add(close_req_valid_o=1,close_req_ready_i=1,close_req_sequence_o=0,close_req_token_o=0,
          close_req_job_o=7,close_req_epoch_o=1,close_req_task_sequence_o=1)
    d.add(close_rsp_valid_i=1,close_rsp_ready_o=1,close_rsp_sequence_i=0,close_rsp_token_i=0,
          close_rsp_job_i=7,close_rsp_epoch_i=1,close_rsp_task_sequence_i=1)
    d.add(trace_cancel_token_retire_o=1)
    d.add(trace_cancel_object_drop_o=1)
    terminal = codec.pack_record("event_message",dict(kind=3,source_block=0,job_id=7,epoch=1,
        task_sequence=1,completion_token=0,status=11,flags=4))
    d.add(event_valid_o=1,event_ready_i=1,event_packet_o=int.from_bytes(terminal,"little"))
    d.life,d.seq = "READY","IDLE"; d.add()
    traces = [a.result("empty_local"),b.result("M_clear_backpressure"),c.result("prepare_then_deploy"),
              d.result("cancel_passive_RX_close")]
    for trace in traces:
        check_cycles.check_trace(trace)
    packet = codec.pack_record("task_message",dict(kind=0,target_block=0,job_id=7,epoch=1,
        task_sequence=1,completion_token=0,program_image_id=100,topology_id=393400001))
    flits = []
    for index in range(16):
        value = hex(int.from_bytes(packet[index*4:index*4+4],"little"))
        if index in (0,15):
            flits.append(dict(valid=1,ready=0,data=value,packet_accepted=False))
        flits.append(dict(valid=1,ready=1,data=value,packet_accepted=index == 15))
    check_cycles.check_flits(packet,flits)
    return dict(schema="authored-local-boundary-examples/0.1",traces=traces,
                flit_example=dict(packet_hex=packet.hex(),cycles=flits),rtl_tested=False,
                controller_execution=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args = parser.parse_args()
    data = (json.dumps(build(),ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    file = HERE/"timing_examples.json"
    if args.check:
        assert file.read_bytes() == data,"authored boundary examples differ"
    else:
        file.write_bytes(data)
    print("PASS 4 authored boundary examples + 1 flit example; not RTL execution")


if __name__ == "__main__":
    main()
