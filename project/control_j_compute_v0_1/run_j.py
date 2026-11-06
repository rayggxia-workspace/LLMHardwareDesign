"""Admit J's two-word lease image and verify the native T/E/S trial."""
import struct
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"control_jc_trial_v0_1"))
from trial import (BINDINGS,PROJECT,GUARD,action,assert_trace,check_holds,codec,h,image_pair,
                   run_trial,traces,verify_sources)

PROFILE=BINDINGS["profiles"]["J"]
OP=int(PROFILE["operation"],16)
CASES=[
    ("two_word_fragment",(4,8,12,16),0,(0,),None),
    ("consecutive_boundary_stall",(0,2,1020,1022),2,(0,1),None),
    ("reject_abi_then_load",(4,8,12,16),1,(0,),"BADCFG"),
    ("reject_unaligned",(4,8,12,16),0,(0,),"odd"),
    ("reject_aliased_pairs",(4,8,12,16),1,(0,),"alias"),
    ("reject_reserved_bits",(4,8,12,16),0,(0,),"reserved"),
    ("missing_second_word_revokes",(4,8,12,16),2,(0,),"JMISSING"),
    ("wrong_first_index_revokes",(4,8,12,16),1,(0,),"JORDER"),
    ("e_error_leaves_only_scratch",(4,8,12,16),1,(1,),"JEFAULT"),
]
REJECT={"odd","alias","reserved"}


def images(a,b,scratch,dst):
    if len({a,b,scratch,dst})!=4 or any(x%2 or not 0<=x<=1022 for x in (a,b,scratch,dst)):
        raise ValueError("J pair range, overlap or alignment")
    ex=dict(resource=PROFILE["service_resource"],service=0,native_op=OP,native_abi_id=PROFILE["abi"],
            native0=a | b<<10 | scratch<<20,native1=dst)
    return image_pair(PROFILE,17940,ex)


def admit(mother,local):
    if len(local)!=368:
        raise ValueError("J image length")
    d=codec.unpack_record("execution",local[-128:])
    w=d["native0"]
    if (mother,local)!=images(w&1023,(w>>10)&1023,(w>>20)&1023,d["native1"]&1023):
        raise ValueError("J image or descriptor not canonical")


def mutated(local,fault):
    d=bytearray(local)
    if fault=="odd":
        d[308] |= 1
    elif fault=="alias":
        d[308:312]=(int.from_bytes(d[304:308],"little")&1023).to_bytes(4,"little")
    elif fault=="reserved":
        d[309] |= 4
    return bytes(d)


def data(index):
    cases=[
        (((200,-140,-2071,107,-1933,302,-1,21),(0,-2,3,-32768,32767,59,-983,102)),
         ((-80,249,123,-212,-45,-200,2,25),(1,4,-2,-1,1,30,-456,33))),
        (((32766,-32767,430,-932,42,-2200,2090,0),(2048,-2048,1024,-1024,15,12,-22,100)),
         ((80,-77,204,199,-144,17,7,21),(-17,80,-81,82,-83,84,85,-86))),
    ]
    return cases[index]


def pack(values):
    return int.from_bytes(struct.pack("<8h",*values),"little")


def sat_add(a,b):
    sums=[x+y for x,y in zip(a,b)]
    clamped=[max(-32768,min(32767,v)) for v in sums]
    return pack(clamped),int(sums!=clamped)


def prepare_case(case):
    _,addresses,stall,seeds,fault=case
    a,b,scratch,dst=addresses
    mother,local=images(*addresses)
    admit(mother,local)
    if fault in REJECT:
        local=mutated(local,fault)
        try:
            admit(mother,local)
        except ValueError:
            pass
        else:
            raise AssertionError("J invalid descriptor admitted")
    writes=[]
    for seed in seeds:
        x,y=data(seed)
        writes.append([action(0,a+i,pack(x[i])) for i in range(2)]+
                      [action(0,b+i,pack(y[i])) for i in range(2)]+
                      [action(0,k+i,GUARD) for k in (scratch,dst) for i in range(2)])
    reads=[[action(0,k+i) for k in (scratch,dst) for i in range(2)] for _ in seeds]
    status=5 if fault in REJECT else 9 if fault in {"JMISSING","JORDER","JEFAULT"} else 0
    flags=["+"+fault] if fault and fault not in REJECT else []
    return mother,local,[],writes,reads,[status]*len(seeds),stall,flags


def audit(log,case,statuses):
    _,(a,b,scratch,dst),stall,seeds,fault=case
    results=[]
    for j,((group,ev),status,seed) in enumerate(zip(traces(log,len(seeds),fault=="BADCFG"),statuses,seeds)):
        x,y=data(seed)
        xp,yp=[pack(v) for v in x],[pack(v) for v in y]
        job,seq=7+j,j+1
        expected=[("CALL",job,1,seq)]
        out=[GUARD]*4
        reads=writes=saturated=0
        if fault not in REJECT:
            expected += [("EXEC",job,1,seq,6),("TBEGIN",seq),("READ",a),("READ_RSP",h(xp[0]))]
            reads=16
            if fault=="JORDER":
                expected += [("TREVOKE",1)]
            else:
                expected += [("TFILL",0,h(xp[0])),("READ",a+1),("READ_RSP",h(xp[1]))]
                reads=32
                if fault=="JMISSING":
                    expected += [("TREVOKE",0)]
                else:
                    expected += [("TFILL",1,h(xp[1])),("TCOMMIT",seq,2)]
                    for i in range(2):
                        expected += [("WRITE",scratch+i,h(xp[i])),("ACK",h(xp[i])),("TTAKE",i,i,h(xp[i]))]
                        out[i]=xp[i]
                        writes+=16
                    expected += [("TREL",seq)]
                    for i in range(2):
                        expected += [("READ",scratch+i),("READ_RSP",h(xp[i])),("READ",b+i),("READ_RSP",h(yp[i])),
                                     ("EIN",14 if fault=="JEFAULT" else 0,0,h(xp[i]),h(yp[i]))]
                        reads+=32
                        if fault=="JEFAULT":
                            expected += [("EOUT",1,0,h(0))]
                            break
                        val,flag=sat_add(x[i],y[i])
                        expected += [("EOUT",0,flag,h(val)),("WRITE",dst+i,h(val)),("ACK",h(val))]
                        out[2+i]=val
                        writes+=16
                        saturated |= flag
            expected += [("SERVICE",job,status,reads,writes,saturated)]
        expected += [("TERMINAL",job,status,reads,writes,saturated),("RESULT",job,status,reads,writes,saturated)]
        expected += [("READBACK",job,0,k+i,h(out[2*j2+i])) for j2,k in enumerate((scratch,dst)) for i in range(2)]
        assert_trace(group,expected)
        if not status:
            assert [v[0] for _,v in ev["RETIRE"]]==["41","44","4f"]
        held={kind.lower():check_holds(ev,kind,stall*mult)
              for kind,mult in (("TREL",3),("EIN",2),("EOUT",3),("WRITE",4),("ACK",5))}
        if fault=="JMISSING":
            assert [v for _,v in ev["TFILL_H"][-64:]]==[["1",h(xp[1])]]*64
        elif fault!="JORDER":
            check_holds(ev,"TFILL",stall*2)
        for take,(cycle,value) in enumerate(ev["TTAKE"]):
            assert ev["ACK"][take][0]<cycle
            offered=[(t,v) for t,v in ev["TTAKE_H"] if v[0]==str(take)]
            assert offered and offered[0][0]<=ev["WRITE"][take][0]
            assert all(t<cycle and v==value for t,v in offered)
        if ev["TREL"]:
            assert ev["TTAKE"][-1][0]<ev["TREL"][0][0]<ev["EIN"][0][0]
        results.append(dict(job=job,status=status,read_bytes=reads,write_bytes=writes,saturated=bool(saturated),
                            readback=list(map(h,out)),held=held,
                            cycles={k.lower():[c for c,_ in ev[k]] for k in ("CALL","TFILL","TCOMMIT","ACK","TTAKE",
                                    "TREL","TREVOKE","EIN","EOUT","WRITE","SERVICE","RESULT","READBACK")}))
    return results


if __name__=="__main__":
    verify_sources(("T","E","S","SA","SB"))
    run_trial("J73",PROFILE,"TB_J_LEASE",HERE,
              [HERE/"t_native_lint.vlt",HERE/"lc_j_lease_adapter.sv",PROJECT/"rtl/block_v1/transaction6k.sv"],
              CASES,prepare_case,audit)
