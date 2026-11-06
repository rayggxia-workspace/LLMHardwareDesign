"""Compile the real U/N/E/S trial and verify command, data and retirement traces."""
import argparse
from collections import defaultdict
import json
from math import isqrt
import os
from pathlib import Path
import struct
import sys

from u_images import ABI, TOPOLOGY, images, validate_pair, validate_sources
from run_a2 import CTRL, PROJECT, SOURCES, SENTINEL, common, mem, rne

HERE = Path(__file__).resolve().parent
CASES = [
    ("two_segments", (4,9,20,8,5,1024,256), 0, (0,), None),
    ("boundary_stalled_saturation", (1021,5,1022,3,5,1024,32760), 2, (0,1), None),
    ("zero_vector", (4,9,20,1,1,1,-7), 1, (2,), None),
    ("reject_config_then_load", (4,9,20,8,5,0xffffffff,-128), 1, (1,), "UBADCFG"),
    ("reject_destination_overflow", (4,9,1022,8,5,1024,256), 0, (0,), "destination"),
    ("reject_tail_overlap", (4,9,20,8,5,1024,256), 1, (0,), "alias"),
    ("reject_zero_count", (4,9,20,8,5,1024,256), 1, (0,), "count"),
    ("reject_zero_epsilon", (4,9,20,8,5,1024,256), 1, (0,), "epsilon"),
    ("native_early_replay", (4,9,20,8,5,1024,256), 2, (0,), "UEARLY"),
    ("native_replay_overcount", (4,9,20,8,5,1024,256), 2, (0,), "UCOUNT"),
    ("second_e_error_no_write", (4,9,20,8,5,1024,256), 2, (0,), "UEFAULT"),
    ("second_ack_corrupt", (4,9,20,8,5,1024,256), 2, (0,), "UACKFAULT"),
]
REJECT = {"destination","alias","count","epsilon"}
FAIL = {"UEARLY","UCOUNT","UEFAULT","UACKFAULT"}
GAMMA = int.from_bytes(struct.pack("<8h", *([1024]*8)), "little")
GUARD = int.from_bytes(SENTINEL,"little")


def vectors(i):
    return [((-1350,1740,-21,320,5000,-1229,90,803), (991,-333,53,-280,-4134,770,-22,520)),
            ((32767,-32768,990,-133,600,887,-642,200), (990,9000,-800,220,7,-888,3223,-747)),
            ((0,)*8,(0,)*8)][i]


def pack(values):
    return int.from_bytes(struct.pack("<8h", *(list(values)+[0]*(8-len(values)))), "little")


def source_word(values, count):
    return pack(list(values[:count])+[0x65a1]*(8-count))


def seeds(i, n0, n1):
    a,b = vectors(i)
    return (source_word(a,n0).to_bytes(16,"little")+bytes(48)
            +source_word(b,n1).to_bytes(16,"little")+bytes(48)+SENTINEL)


def mutated(local, fault):
    data = bytearray(local)
    native0 = int.from_bytes(data[304:308],"little")
    if fault=="destination":
        native0=(native0 & ((1<<20)-1)) | 1023<<20
    if fault=="alias":
        native0=(native0 & ~1023) | ((native0>>20)+1)
    data[304:308]=native0.to_bytes(4,"little")
    if fault=="count":
        data[308] &= 0xf0
    if fault=="epsilon":
        data[312:316]=bytes(4)
    return bytes(data)


def saturate(value):
    return max(-32768, min(32767,value))


def reference(vectors, counts, epsilon, bias):
    active = [vec[:count] for vec,count in zip(vectors,counts)]
    squares = sum(x*x for segment in active for x in segment)
    root = isqrt(((squares<<16)//sum(counts))+(epsilon<<16))
    factor = (1<<38)//root
    expected = []
    for segment in active:
        wide = [rne(x*factor*1024,30) for x in segment]
        normalized = [saturate(x) for x in wide]
        shifted = [x+bias for x in normalized]
        outputs = [saturate(x) for x in shifted]
        expected.append((pack(normalized), int(wide!=normalized), pack(outputs), int(shifted!=outputs)))
    return factor,expected


def h(word):
    return f"{word:032x}"


def audit(log, spec, stall, ids, fault, status):
    a,b,dst,n0,n1,eps,bias = spec
    rows = [(int(f[1]), f[2], f[3:]) for line in log.splitlines()
            if (f:=line.split()) and f[0] in ("A2","U73")]
    calls=[i for i,(_,k,_) in enumerate(rows) if k=="CALL"]
    assert len(calls)==len(ids)
    cfg=rows[:calls[0]]
    assert [v for _,k,v in cfg if k=="CONFIG_READBACK"]==[["23"]]
    assert sum(k=="BAD_ABI_REJECTED" for _,k,_ in cfg)==(fault=="UBADCFG")
    results=[]
    for j, ident in enumerate(ids):
        group=rows[calls[j]:calls[j+1] if j+1<len(calls) else len(rows)]
        events=defaultdict(list)
        for cycle,kind,fields in group:
            events[kind].append((cycle,fields))
        job=7+j
        order=j+1
        reads=0
        confirmed=0
        visible=0
        sat=0
        lane_words=[GUARD,GUARD]
        wanted=[]
        factor, ref=reference(vectors(ident),(n0,n1),eps,bias)

        def ev(name, *fields):
            wanted.append((name,list(map(str,fields))))

        def rd(address, word):
            nonlocal reads
            ev("READ",address);ev("READ_RSP",h(word))
            reads+=16

        def n(op,count=0,param=0,data=0,aux=0,error=0,satur=0,result=0):
            ev("NIN",op,count,param,h(data),h(aux))
            ev("NOUT",error,satur,h(result))

        ev("CALL",job,1,order,2)
        if fault not in REJECT:
            ev("EXEC",job,1,order,0,3,1)
            word0,word1=(source_word(v,c) for v,c in zip(vectors(ident),(n0,n1)))
            n(0,param=1,data=eps)
            rd(a,word0);n(1,n0,data=word0)
            rd(b,word1);n(1,n1,data=word1)
            if fault=="UEARLY":
                n(5,1,error=1)
            else:
                n(2)
                for segment,(address,count,word) in enumerate(zip((a,b),(n0,n1),(word0,word1))):
                    rd(address,word)
                    if segment==1 and fault=="UCOUNT":
                        n(5,count+1,data=word,aux=GAMMA,error=1)
                        break
                    normalized,n_sat,output,e_sat=ref[segment]
                    n(5,count,data=word,aux=GAMMA,satur=n_sat,result=normalized)
                    sat |= n_sat
                    e_fault=segment==1 and fault=="UEFAULT"
                    ev("EIN",14 if e_fault else 0,h(normalized),h(pack([bias]*count)))
                    ev("EOUT",int(e_fault),0 if e_fault else e_sat,h(0 if e_fault else output))
                    if e_fault:
                        break
                    sat |= e_sat
                if fault not in ("UCOUNT","UEFAULT"):
                    for segment,(_,_,output,_) in enumerate(ref):
                        ev("WRITE",dst+segment,h(output))
                        corrupt=segment==1 and fault=="UACKFAULT"
                        ev("ACK",h(output),h(output^int(corrupt)))
                        confirmed+=0 if corrupt else 16
                        visible+=16
                        lane_words[segment]=output
            ev("SERVICE",job,1,order,0,3,status,reads,confirmed,sat)
        ev("TERMINAL",job,1,order,2,status,reads,confirmed)
        ev("RESULT",job,1,order,status,reads,confirmed)
        for segment,word in enumerate(lane_words):
            ev("READBACK",job,dst+segment,h(word))

        actual=[(kind,fields) for _,kind,fields in group if not kind.endswith("_H")
                and kind not in ("RETIRE","LC_SAT","MC_SAT")]
        assert actual==wanted, next(((i,x,y) for i,(x,y) in enumerate(zip(actual,wanted)) if x!=y),
                                     (len(actual),len(wanted)))
        assert [v for _,v in events["LC_SAT"]]==[list(str(sat))]==[v for _,v in events["MC_SAT"]]
        if not status:
            assert [v[0] for _,v in events["RETIRE"]]==["41","44","4f"]
        held_cycles={}
        for name,mult in (("NIN",2),("NOUT",3),("EIN",2),("EOUT",3),("WRITE",4),("ACK",5)):
            handshake=events[name]
            held=events[name+"_H"]
            held_cycles[name.lower()]=len(held)
            assert len(held)==len(handshake)*stall*mult,(name,held,handshake)
            for k,(tick,value) in enumerate(handshake):
                part=held[k*stall*mult:(k+1)*stall*mult]
                assert all(cycle<tick and payload==value for cycle,payload in part),name
        result=dict(job=job,task=order,status=status,read_bytes=reads,confirmed_write_bytes=confirmed,
                    actual_write_bytes=visible,readback=list(map(h,lane_words)),saturated=bool(sat),
                    factor_reference=factor, held_cycles=held_cycles,
                    cycles={k.lower():[t for t,_ in events[k]] for k in
                            ("CALL","READ","NIN","NOUT","EIN","EOUT","WRITE","ACK","SERVICE","TERMINAL","RESULT","READBACK")})
        results.append(result)
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator",default="verilator")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    validate_sources()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ)
    ndir=PROJECT/"rtl/block_v2"
    sources=[p for p in SOURCES if p.name not in ("block_v2_m.sv","lc_m_dot_store_adapter.sv","block_feed_loader.sv")]
    sources += [HERE/"tb_u_local.sv",HERE/"lc_u_rms_adapter.sv",ndir/"block_v2_n.sv",
                ndir/"block_v2_n_group.sv",ndir/"block_v2_e.sv"]
    exe=out/"obj_dir/sim"
    cmd=[args.verilator,"--binary","--timing","--timescale","1ns/1ps","--top-module","tb_p_compute",
         "-I"+str(CTRL),"-I"+str(ndir),"-DTB_U_COMPUTE",
         "--Mdir",exe.parent,"-j",env.get("SLURM_CPUS_PER_TASK","4"),"-o",exe.name,*sources]
    compile_log=out/"compile.log"
    common.run(cmd,out,env,compile_log)
    results=[]
    for name,spec,stall,ids,fault in CASES:
        folder=out/name
        folder.mkdir()
        mother,local=images(*spec)
        validate_pair(mother,local)
        if fault in REJECT:
            local=mutated(local,fault)
            try:
                validate_pair(mother,local)
            except ValueError:
                pass
            else:
                raise AssertionError("host admitted injected U descriptor")
        a,b,dst,n0,n1,_,_=spec
        for stem,data in (("mother",mother),("local",local),("seed",b"".join(seeds(i,n0,n1) for i in ids))):
            (folder/(stem+".bin")).write_bytes(data)
            mem(folder/(stem+".mem"),data)
        status=5 if fault in REJECT else 9 if fault in FAIL else 0
        launch=[exe,f"+MOTHER={folder/'mother.mem'}",f"+LOCAL={folder/'local.mem'}",
                f"+MWORDS={len(mother)//16}",f"+LWORDS={len(local)//16}",f"+SEED={folder/'seed.mem'}",
                f"+A={a}",f"+B={b}",f"+DST={dst}",f"+STALL={stall}",f"+RUNS={len(ids)}",f"+EXPECT={status}"]
        if fault in FAIL or fault=="UBADCFG":
            launch.append("+"+fault)
        log=common.run(launch,out,env,folder/"run.log")
        assert f"PASS A2 jobs={len(ids)} status={status}" in log
        jobs=audit(log,spec,stall,ids,fault,status)
        results.append(dict(case=name,spec=spec,expected_status=status,jobs=jobs,
                            command=list(map(str,launch)),sha256={
                                f.name:common.sha(f.read_bytes()) for f in sorted(folder.iterdir())}))
        print(name,"PASS",flush=True)
    report=dict(schema="control-u-rms-store/0.1",abi=ABI,topology=TOPOLOGY,cases=results,
                actual_rtl=["mc_min_controller","lc_min_controller","block_local_s_macro","block_v2_n","block_v2_e"],
                compile_command=list(map(str,cmd)),compile_log_sha256=common.sha(compile_log.read_bytes()),
                python=sys.version,verilator=common.run([args.verilator,"--version"],out,env).strip(),
                scope="single U fixed wiring, two-segment RMS and E ADD")
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("PASS U73",len(results),"RTL scenarios",flush=True)


if __name__=="__main__":
    main()
