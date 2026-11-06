"""Validate the native U, J and C handoffs with two real local controllers."""

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
P = PROJECT / "control_p_compute_v0_1"
R4 = PROJECT / "control_r4_v0_1"
JC = PROJECT / "control_jc_trial_v0_1"
for folder in (P, R4, JC, *(PROJECT / f"control_{kind}_compute_v0_1" for kind in "ujc")):
    sys.path.insert(0, str(folder))

from run_handoff import CTRL, RAW_ABI, SOURCES, assemble, common, mem, parse_image
from run_a2 import rne, silu_reference
from trial import action, codec, verify_sources
import run_u
import run_j
import run_c
import stored_ack_check

TOPOLOGY = {"u": 0x1764B303, "j": 0x1764E303, "c": 0x1764C303}
NATIVE_ABI = {"u": 0x00017904, "j": 0x00017905, "c": 0x00017906}
CLOCK_NS = "3.333333333"


def producer(kind):
    if kind == "u":
        spec = (4, 8, 12, 8, 5, 1024, 256)
        _, local = run_u.images(*spec)
        a, b = run_u.vectors(0)
        _, ref = run_u.reference((a, b), spec[3:5], *spec[5:])
        seed = [action(0, 4, run_u.source_word(a, 8)), action(0, 8, run_u.source_word(b, 5))]
        return local, 12, seed, [part[2] for part in ref]
    if kind == "j":
        _, local = run_j.images(4, 8, 20, 12)
        a, b = run_j.data(0)
        seed = [action(0, base+i, run_j.pack(row)) for base, pair in ((4, a), (8, b))
                for i, row in enumerate(pair)]
        return local, 12, seed, [run_j.sat_add(x, y)[0] for x, y in zip(a, b)]

    dst = 12
    decay = 0x40000000
    _, local = run_c.images(dst, decay)
    seed = [action(bank+2, i, value) for bank, lanes in enumerate((run_c.SEEDS[0], run_c.SHADOW))
            for i, value in enumerate(run_c.state_words(lanes))]
    state = run_c.SEEDS[0]
    ref = []
    for _ in range(2):
        state = tuple(rne(x*decay, 31) for x in state)
        clipped = [max(-32768, min(32767, rne(x, 6))) for x in state[:2]]
        ref.append(run_c.word([silu_reference(x) for x in clipped], 16))
    return local, dst, seed, ref


def images(kind):
    local, dst, seed, expected = producer(kind)
    bundles = json.loads((PROJECT/"control_image_v0_1/bundles.json").read_bytes())["bundles"]
    raw = next(b["images_hex"] for b in bundles if b["manifest"]["bundle"] == "receiver_first_16B")
    mc, raw_src, sink = (parse_image(bytes.fromhex(raw[key]), role) for key, role in
                         (("mother", "mother"), ("local0", "local"), ("local1", "local")))
    execution = codec.unpack_record("execution", local[-128:])
    native_task = codec.unpack_record("task", local[-192:-128])
    topology = TOPOLOGY[kind]
    abi = NATIVE_ABI[kind]
    mask = native_task["required_resources"]
    source_id = {"u": 17971, "j": 17981, "c": 17991}[kind]
    width = 16 if kind == "c" else 32

    def object_at(template, addr, native_abi):
        return dict(template, base_bytes=16*addr, capacity_bytes=width, length_bytes=width,
                    native_abi_id=native_abi)

    def transfer(template):
        return dict(template, count_bytes=width, max_fragment_bytes=width)

    program = [dict(op="L_EXEC", a=execution["resource"], b=3), dict(op="L_WAIT", x=8)]
    native_task = dict(native_task, program_image_id=source_id, topology_id=topology)
    records = dict(task=[native_task], execution=[execution])
    if kind != "c":
        native_task.update(output_object_mask=1, max_steps=7)
        source = raw_src["records"]
        records.update(object=[object_at(source["object"][0], dst, abi)],
                       transfer=[transfer(source["transfer"][1])])
        program = [dict(op="L_OPEN")] + program + [dict(op="L_TX"), dict(op="L_WAIT", x=1), dict(op="L_DROP")]
    program += [dict(op="L_END")]

    sink_records = sink["records"]
    return {
        "mother": assemble("mother", mc["program"], {"event_binding": mc["records"]["event_binding"]},
                           source_id-1, 0, abi, topology),
        "local0": assemble("local", program, records, source_id, mask, abi, topology),
        "local1": assemble("local", sink["program"],
                           dict(task=[dict(sink_records["task"][0], program_image_id=source_id+1, topology_id=topology)],
                                object=[object_at(sink_records["object"][0], 16, RAW_ABI)],
                                transfer=[transfer(sink_records["transfer"][0])]),
                           source_id+1, 0x20, RAW_ABI, topology),
    }, seed, expected


def audit(log, kind, runs, expected, fault, rejected):
    events = defaultdict(list)
    for line in log.splitlines():
        f = line.split()
        if len(f) >= 3 and f[0] in ("N", "CHAIN", "U73", "JC", "ACKG"):
            events[f[0], f[2]].append((int(f[1]), f[3:]))
    guard = stored_ack_check.check(log)
    assert guard["rejected"] == rejected
    calls = events["CHAIN", "CALL"]
    ready = [(c, f) for c, f in events["CHAIN", "EVENT"] if f[:2] == ["1", "0"]]
    assert len(calls)==2*runs and len(ready)==runs
    for i in range(runs):
        rx,tx=calls[2*i:2*i+2]
        assert rx[1]==["1",str(7+i),"1",str(i+1)] and tx[1]==["0",str(7+i),"1",str(i+1)]
        assert rx[0]<ready[i][0]<tx[0]
    stores = events["N", "STORE"]
    txs = events["N", "TX"]
    destinations = events["CHAIN", "DEST_READ"]
    drops = events["CHAIN", "DROP"]
    results = events["CHAIN", "RESULT"]
    missing = fault=="lost"
    per_job = 1 if kind=="c" else 2
    expected_words = expected[:runs] if kind=="c" else expected*runs
    assert len(stores)==len(txs)==per_job*runs
    assert [int(f[-1],16) for _,f in stores]==expected_words
    assert [int(f[-1]) for _,f in txs]==[12+word for _ in range(runs) for word in range(per_job)]
    assert all(tx[0]<store[0] for tx,store in zip(txs,stores))

    if kind=="c":
        pubs=events["JC","PUBLISH"]
        states=events["JC","CSTATE"]
        receipts=events["JC","RECEIPT"]
        assert len(states)==runs
        assert not drops
        assert [int(f[1],16) for _,f in events["JC","CONS"]]==expected_words
        assert [int(f[1],16) for _,f in destinations]==expected_words
        assert [int(f[1],16) for _,f in events["JC","WRITE"]]==expected_words
        if missing:
            assert not pubs and not receipts and not guard["receipts"]
            assert guard["pending"]["commit"]==stores[0][0] and guard["pending"]["accepted"] is None
            assert states[0][1]==["0","0","0"] and results[0][1][1]=="9"
        else:
            assert len(pubs)==len(receipts)==len(guard["receipts"])==runs
            assert [f for _,f in pubs]==[[str((i+1)%2),str(i+1)] for i in range(runs)]
            for i,(ack,pub,receipt,result) in enumerate(zip(guard["receipts"],pubs,receipts,results)):
                assert ack["commit"]==stores[i][0]<ack["released"]==receipt[0]<pub[0]<result[0]
                assert states[i][1]==[str((i+1)%2),str(i+1),"0"]
                assert int(receipt[1][0],16)==ack["identity"]>>144 and receipt[1][1:]==["0","0"]
                assert result[1]==[str(7+i),"0","16","32"]
        assert len(results)==runs and len(destinations)==runs
        return dict(cases=runs,completed=0 if missing else runs,publications=pubs,states=states,
                    receipts=receipts,stores=stores,results=results,readback=destinations,ack_guard=guard)

    source = "U73" if kind=="u" else "JC"
    source_reads=events["CHAIN","SOURCE_READ"]
    local_acks=events[source,"ACK"]
    assert [int(f[1],16) for _,f in source_reads]==expected_words
    assert [int(f[0]) for _,f in source_reads]==[12,13]*runs
    assert len(local_acks)==(2 if kind=="u" else 4)*runs
    count=2 if kind=="u" else 4
    for i in range(runs):
        assert local_acks[count*(i+1)-1][0] < source_reads[2*i][0] < txs[2*i][0]
    if missing:
        assert not drops and not results and not destinations
        assert len(guard["receipts"])==1 and guard["pending"]["accepted"] is None
        assert guard["pending"]["commit"]==stores[1][0]
        assert guard["receipts"][0]["released"]<txs[1][0]
    else:
        assert len(drops)==len(results)==runs and len(destinations)==2*runs
        assert [int(f[1],16) for _,f in destinations]==expected_words
        assert len(guard["receipts"])==2*runs
        for i,(drop,result) in enumerate(zip(drops,results)):
            first,last=guard["receipts"][2*i:2*i+2]
            assert first["commit"]==stores[2*i][0]<first["released"]<txs[2*i+1][0]
            assert last["commit"]==stores[2*i+1][0]<last["released"]<drop[0]<result[0]
            assert first["identity"]&0xffffffff==0 and last["identity"]&0xffffffff==1
            assert result[1]==[str(7+i),"0",*(["96","64"] if kind=="u" else ["128","96"])]
    return dict(cases=runs,completed=0 if missing else runs,stores=stores,drops=drops,
                results=results,readback=destinations,ack_guard=guard)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind",choices=tuple(TOPOLOGY))
    p.add_argument("--verilator",required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    kind=args.kind
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ)
    r=PROJECT/"rtl/block_v2"
    provider=PROJECT/f"control_{kind}_compute_v0_1"
    defines=["TB_COMPUTE_HANDOFF","TB_EXT_HANDOFF","TB_STORED_ACK_GUARD",
             {"u":"TB_U_COMPUTE","j":"TB_J_LEASE","c":"TB_C_STATE"}[kind]]
    sources=SOURCES+[CTRL/"tb_control_network.sv",R4/"tb_real_local.sv",
                     R4/"lc_raw16_s_adapter.sv",R4/"p_stored_ack_guard.sv",r/"block_v2_e.sv"]
    if kind=="u":
        run_u.validate_sources()
        sources += [provider/"tb_u_local.sv",provider/"lc_u_rms_adapter.sv",
                    r/"block_v2_n.sv",r/"block_v2_n_group.sv"]
    elif kind=="j":
        verify_sources(("T","E","S","SA","SB"))
        sources = [provider/"t_native_lint.vlt",*sources,JC/"tb_jc_local.sv",
                   provider/"lc_j_lease_adapter.sv",PROJECT/"rtl/block_v1/transaction6k.sv"]
    else:
        verify_sources(("R","RS","E","G","GT","S","SA","SB"))
        state=PROJECT/"rtl/r_local_state"
        sources = [provider/"r_native_lint.vlt",*sources,JC/"tb_jc_local.sv",r/"block_v2_g.sv",
                   provider/"lc_c_state_adapter.sv",state/"r_state_store.sv",state/"r_stream_local.sv"]
    if kind!="c":
        defines.append("TB_MULTI_HANDOFF")
    obj=out/"obj_dir"
    cmd=[args.verilator,"--binary","--timing","--top-module","tb_control_network",
         *["-D"+d for d in defines], *["-I"+str(x) for x in (P,R4,CTRL,r,provider)],
         "--Mdir",obj,"-j",env.get("SLURM_CPUS_PER_TASK","4"),"-o","sim",*sources]
    compile_log=out/"compile.log"
    common.run(cmd,out,env,compile_log)

    suite=(("single",1,0,0,0),("stalled_two_jobs",2,2,0,0),
           ("duplicate",1,2,6,1 if kind=="c" else 2),
           ("old_receipt",2 if kind=="c" else 1,2,7,1),("lost",1,2,2,0))
    if kind=="c":
        suite += (("wrong_epoch",1,2,5,1),)
    bundle,seed,expected=images(kind)
    results=[]
    for fault,runs,stall,mode,rejected in suite:
        case=out/fault
        case.mkdir()
        argv=[obj/"sim",f"+STALL={stall}",f"+RUNS={runs}",f"+MODE={mode}",f"+CALLS={2*runs}"]
        for key,file_arg,word_arg in (("mother","IMAGE","WORDS"),("local0","LOCAL0","WORDS0"),("local1","LOCAL1","WORDS1")):
            path=case/(key+".mem")
            mem(path,bundle[key])
            argv.extend((f"+{file_arg}={path}",f"+{word_arg}={len(bundle[key])//16}"))
        argv.extend((f"+LOCAL={case/'local0.mem'}",f"+LWORDS={len(bundle['local0'])//16}"))
        path=case/"seed.mem"
        path.write_text("".join(f"{x:036x}\n" for x in seed),encoding="ascii")
        argv.extend((f"+SEED={path}",f"+SEED_WORDS={len(seed)}"))
        if fault=="lost":
            argv.append("+EXPECTED=9" if kind=="c" else "+POISON=1")
        log=common.run(argv,out,env,case/"trace.log")
        assert "PASS network actualMother=1 actualLC=2" in log
        result=audit(log,kind,runs,expected,fault,rejected)
        results.append(dict(case=fault,check=result,command=list(map(str,argv)),
                            sha256={f.name:common.sha(f.read_bytes()) for f in sorted(case.iterdir())}))
        print(kind,fault,"PASS",flush=True)
    report=dict(schema="r736-native-handoff/0.1",kind=kind,topology=hex(TOPOLOGY[kind]),
                mother=1,actual_local_controllers=2,actual_private_s=2,cases=results,
                compile_command=list(map(str,cmd)),compile_log_sha256=common.sha(compile_log.read_bytes()),
                tools=dict(python=sys.version,verilator=common.run([args.verilator,"--version"],out,env).strip()))
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"PASS {kind.upper()} {len(results)} dual-local native cases",flush=True)


if __name__=="__main__":
    main()