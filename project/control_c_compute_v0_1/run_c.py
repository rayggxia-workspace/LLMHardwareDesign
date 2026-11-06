"""Exercise C state publication with native R256/E/G, two real S and one consumer."""
import struct
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"control_jc_trial_v0_1"))
from trial import (BINDINGS,PROJECT,GUARD,action,assert_trace,check_holds,codec,h,image_pair,
                   rne,run_trial,traces,verify_sources)
from run_a2 import silu_reference

PROFILE=BINDINGS["profiles"]["C"]
OP=int(PROFILE["operation"],16)
DEST=21
PEER=19
CASES=[
    ("continuous_publish",DEST,0x40000000,0,0,(0,0),None),
    ("saturation_and_backpressure",1023,0x60000000,2,1,(0,),None),
    ("wrong_epoch_then_valid_receipt",DEST,0x40000000,1,0,(0,),"CWRONG"),
    ("lost_receipt_stale_then_recover",DEST,0x40000000,2,0,(9,0),"CLOST"),
    ("native_r_error_then_recover",DEST,0x40000000,1,0,(9,0),"CRFAULT"),
    ("native_e_error_then_recover",DEST,0x40000000,2,0,(9,0),"CEFAULT"),
    ("consumer_error_then_recover",DEST,0x40000000,1,0,(9,0),"CREJECT"),
    ("reject_abi_then_load",DEST,0x40000000,0,0,(0,),"BADCFG"),
    ("reject_zero_decay",DEST,0x40000000,0,0,(5,),"zero"),
    ("reject_out_of_range_decay",DEST,0x40000000,0,0,(5,),"range"),
    ("reject_reserved_descriptor",DEST,0x40000000,0,0,(5,),"reserved"),
]
REJECT={"zero","range","reserved"}
SEEDS=[
    (196609,-131075,45784,-90432,7,-13,1048573,-114815),
    (0x70000000,-0x70000000,45784,-90432,15,-31,1073741823,-1073741819),
]
SHADOW=(9531701,-23750,62575,-310,-817,91812,-11990,801)


def images(dst,decay):
    if not (0<=dst<1024 and 0<decay<0x80000000):
        raise ValueError("C trial destination or decay range")
    ex=dict(resource=PROFILE["service_resource"],service=0,native_op=OP,native_abi_id=PROFILE["abi"],
            native0=dst,native1=decay)
    return image_pair(PROFILE,17950,ex)


def admit(mother,local):
    if len(local)!=368:
        raise ValueError("C image length")
    d=codec.unpack_record("execution",local[-128:])
    if (mother,local)!=images(d["native0"],d["native1"]):
        raise ValueError("C trial image or descriptor not canonical")


def word(values,bits):
    code={16:"h",32:"i",64:"q"}[bits]
    return int.from_bytes(struct.pack("<"+str(len(values))+code,*values),"little")


def state_words(lanes):
    return [word(lanes[i:i+4],32) for i in (0,4)]


def prepare_case(case):
    _,dst,decay,stall,seed,status,fault=case
    mother,local=images(dst,decay)
    admit(mother,local)
    if fault in REJECT:
        data=bytearray(local)
        if fault=="zero":
            data[308:312]=bytes(4)
        elif fault=="range":
            data[311]|=0x80
        else:
            data[312]=1
        local=bytes(data)
        try:
            admit(mother,local)
        except ValueError:
            pass
        else:
            raise AssertionError("C bad descriptor admitted")
    initial=[action(bank+2,i,x) for bank,lanes in enumerate((SEEDS[seed],SHADOW))
             for i,x in enumerate(state_words(lanes))]
    seeds=[[action(0,dst,GUARD),action(1,PEER,GUARD)] for _ in status]
    reads=[[action(0,dst),action(1,PEER)]+[action(bank,i) for bank in (2,3) for i in range(2)] for _ in status]
    flags=["+"+fault] if fault and fault not in REJECT else []
    return mother,local,initial,seeds,reads,status,stall,flags


def audit(log,case,statuses):
    _,dst,decay,stall,seed,_,fault=case
    banks=[SEEDS[seed],SHADOW]
    active=version=0
    stale=0
    results=[]
    for j,((group,ev),status) in enumerate(zip(traces(log,len(statuses),fault=="BADCFG"),statuses)):
        job,seq=7+j,j+1
        old_bank,old_version=active,version
        expected=[("CALL",job,1,seq)]
        result=GUARD
        reads=writes=sat=0
        changed_shadow=False
        if fault not in REJECT:
            expected += [("EXEC",job,1,seq,4),("RREAD",active),("RREAD_RSP",h(state_words(banks[active])[0])),
                         ("RLOAD",f"{decay:08x}"),("RCMD",active,0 if fault=="CRFAULT" and j==0 else 1)]
            if fault=="CRFAULT" and j==0:
                expected += [("RRSP",1,"0"*128)]
            else:
                candidate=tuple(rne(x*decay,31) for x in banks[active])
                banks[1-active]=candidate
                changed_shadow=True
                candidate_word=state_words(candidate)[0]
                expected += [("RRSP",0,f"{word(candidate,64):0128x}"),("RREAD",1-active),("RREAD_RSP",h(candidate_word))]
                e_fail=fault=="CEFAULT" and j==0
                expected += [("EIN",14 if e_fail else 13,6,h(candidate_word),h(0))]
                if e_fail:
                    expected += [("EOUT",1,0,h(0))]
                else:
                    narrowed=[rne(x,6) for x in candidate[:4]]
                    clipped=[max(-32768,min(32767,x)) for x in narrowed]
                    sat=int(narrowed!=clipped)
                    expected += [("EOUT",0,sat,h(word(clipped,16))),("GIN",f"{word(clipped[:2],16):08x}")]
                    result=word([silu_reference(x) for x in clipped[:2]],16)
                    expected += [("GOUT",0,0,f"{result:08x}"),("WRITE",dst,h(result)),("ACK",h(result)),
                                 ("READ",dst),("READ_RSP",h(result))]
                    reads=writes=16
                    ident=(job<<96)|(1<<64)|(seq<<32)|(version+1)
                    expected += [("CONS",h(ident),h(result)),("CWRITE",h(result)),("CACK",h(result))]
                    if fault=="CLOST" and j==0:
                        stale=ident
                        expected += [("CONS_DROP",h(ident))]
                    else:
                        if fault=="CWRONG" or fault=="CLOST":
                            bad_id=stale if fault=="CLOST" else ident^(1<<64)
                            expected += [("RECEIPT",h(bad_id),0,1)]
                        bad=fault=="CREJECT" and j==0
                        expected += [("RECEIPT",h(ident),int(bad),0)]
                        if not bad:
                            version+=1
                            active=1-active
            expected += [("SERVICE",job,status,reads,writes,sat)]
            assert [v for _,v in ev["CSTATE"]]==[[str(active),str(version),"0"]]
        else:
            assert not ev["CSTATE"]
        expected += [("TERMINAL",job,status,reads,writes,sat),("RESULT",job,status,reads,writes,sat),
                     ("READBACK",job,0,dst,h(result)),("READBACK",job,1,PEER,h(result))]
        expected += [("READBACK",job,bank+2,i,h(v)) for bank,lanes in enumerate(banks)
                     for i,v in enumerate(state_words(lanes))]
        assert_trace([row for row in group if row[1] not in ("PUBLISH","CSTATE")],expected)
        if status:
            assert version==old_version and active==old_bank and not ev["PUBLISH"]
        else:
            assert [v for _,v in ev["PUBLISH"]]==[[str(active),str(version)]]
            assert ev["CACK"][0][0]<ev["RECEIPT"][-1][0]<ev["PUBLISH"][0][0]<ev["RESULT"][0][0]
            assert [v[0] for _,v in ev["RETIRE"]]==["41","44","4f"]
        if fault=="CLOST" and j==0:
            assert ev["SERVICE"][0][0]-ev["CONS"][0][0]>=96
        held={k.lower():check_holds(ev,k,stall*multiple) for k,multiple in (
            ("EIN",2),("EOUT",3),("GIN",2),("GOUT",3),("WRITE",4),("ACK",5))}
        results.append(dict(job=job,status=status,active_before=old_bank,active_after=active,
                            version_before=old_version,version_after=version,shadow_written=changed_shadow,
                            source_write_bytes=writes,consumer_stored=bool(ev["CACK"]),held=held,
                            receipts=[v for _,v in ev["RECEIPT"]],
                            cycles={k.lower():[c for c,_ in ev[k]] for k in (
                                "CALL","RREAD","RCMD","RRSP","EIN","EOUT","GIN","GOUT","ACK","READ","CONS",
                                "CWRITE","CACK","RECEIPT","PUBLISH","SERVICE","RESULT","READBACK")}))
    return results


if __name__=="__main__":
    verify_sources(("R","RS","E","G","GT","S","SA","SB"))
    run_trial("C73",PROFILE,"TB_C_STATE",HERE,
              [HERE/"r_native_lint.vlt",HERE/"lc_c_state_adapter.sv",PROJECT/"rtl/r_local_state/r_state_store.sv",
               PROJECT/"rtl/r_local_state/r_stream_local.sv",PROJECT/"rtl/block_v2/block_v2_g.sv"],
              CASES,prepare_case,audit)
