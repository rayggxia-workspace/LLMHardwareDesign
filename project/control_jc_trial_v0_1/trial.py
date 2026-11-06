"""Shared fixed-wiring controller trial build, loader and trace helpers."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
sys.path.insert(0,str(PROJECT/"control_p_compute_v0_1"))
from run_a2 import assemble, common, mem, CTRL, SOURCES, SENTINEL, rne
from image import codec

BINDINGS=json.loads((PROJECT/"control_f_compute_v0_1/trial_bindings.json").read_bytes())
GUARD=int.from_bytes(SENTINEL,"little")


def h(value):
    return f"{value:032x}"


def verify_sources(names):
    for name in names:
        entry=BINDINGS["sources"][name]
        data=(PROJECT.parent/entry["path"]).read_bytes()
        actual=hashlib.sha1(f"blob {len(data)}\0".encode("ascii")+data).hexdigest()
        if actual!=entry["blob"]:
            raise ValueError(f"wrong source bytes: {name}")


def image_pair(profile, mother_id, execution):
    local_id=mother_id+1
    abi,top=profile["abi"],profile["topology"]
    resource,mask=profile["service_resource"],profile["resource_mask"]
    mother=assemble("mother",[dict(op="G_CALL",a=0,b=2,c=0),dict(op="G_WAIT",x=4),dict(op="G_END")],
                    {},mother_id,0,abi,top)
    task=dict(block_type=profile["block_type"],entry_pc=0,max_steps=3,required_resources=mask,
              program_image_id=local_id,topology_id=top,native_abi_id=abi)
    local=assemble("local",[dict(op="L_EXEC",a=resource,b=3,c=0),dict(op="L_WAIT",x=8),dict(op="L_END")],
                   dict(task=[task],execution=[execution]),local_id,mask,abi,top)
    return mother,local


def traces(log, jobs, bad_config):
    rows=[(int(fields[1]),fields[2],fields[3:]) for line in log.splitlines()
          if (fields:=line.split()) and fields[0]=="JC"]
    starts=[i for i,(_,kind,_) in enumerate(rows) if kind=="CALL"]
    assert len(starts)==jobs
    setup=rows[:starts[0]]
    assert [data for _,kind,data in setup if kind=="CONFIG_READBACK"]==[["23"]]
    assert sum(kind=="BAD_ABI_REJECTED" for _,kind,_ in setup)==bad_config
    for index,start in enumerate(starts):
        group=rows[start:starts[index+1] if index+1<jobs else len(rows)]
        events=defaultdict(list)
        for cycle,kind,data in group:
            events[kind].append((cycle,data))
        yield group,events


def check_holds(events, name, per_transfer):
    accepted=events[name]
    held=events[name+"_H"]
    assert len(held)==len(accepted)*per_transfer,(name,len(held),len(accepted))
    for i,(cycle,data) in enumerate(accepted):
        assert all(c<cycle and v==data for c,v in held[i*per_transfer:(i+1)*per_transfer]),name
    return len(held)


def assert_trace(group, expected):
    actual=[(kind,data) for _,kind,data in group if not kind.endswith("_H") and kind!="RETIRE"]
    expected=[(kind,[str(v) for v in fields]) for kind,*fields in expected]
    assert actual==expected, next(((i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y),
                                 (len(actual),len(expected),actual[len(expected):],expected[len(actual):]))


def action(device,word,data=0):
    assert 0<=device<16 and 0<=word<1024 and 0<=data<1<<128
    return device<<138 | word<<128 | data


def run_trial(stage, profile, define, directory, rtl, cases, prepare_case, audit):
    parser=argparse.ArgumentParser()
    parser.add_argument("--verilator",default="verilator")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ)
    sources=[p for p in SOURCES if p.name not in ("block_v2_m.sv","lc_m_dot_store_adapter.sv",
                                                  "block_feed_loader.sv","tb_p_compute.sv")]
    sources += [HERE/"tb_jc_trial.sv",HERE/"tb_jc_local.sv",PROJECT/"rtl/block_v2/block_v2_e.sv",*rtl]
    exe=out/"obj_dir/sim"
    cmd=[args.verilator,"--binary","--timing","--timescale","1ns/1ps","--top-module","tb_jc_trial",
         "-I"+str(CTRL),"-I"+str(directory),"-I"+str(PROJECT/"rtl/block_v2"),"-D"+define,
         "--Mdir",exe.parent,"-j",env.get("SLURM_CPUS_PER_TASK","4"),"-o",exe.name,*sources]
    compile_log=out/"compile.log"
    common.run(cmd,out,env,compile_log)
    results=[]
    for case in cases:
        name=case[0]
        mother,local,initial,seeds,readbacks,status,stall,flags=prepare_case(case)
        runs=len(status)
        assert len(seeds)==len(readbacks)==runs and 1<=runs<=4
        sw,rw=len(seeds[0]),len(readbacks[0])
        assert all(len(x)==sw for x in seeds) and all(len(x)==rw for x in readbacks)
        folder=out/name
        folder.mkdir()
        for kind,data in (("mother",mother),("local",local)):
            mem(folder/(kind+".mem"),data)
            (folder/(kind+".bin")).write_bytes(data)
        actions=list(initial)
        for sd,rb in zip(seeds,readbacks):
            actions.extend(sd+rb)
        (folder/"actions.mem").write_text("".join(f"{value:036x}\n" for value in actions),encoding="ascii")
        statuses=sum(s<<(16*i) for i,s in enumerate(status))
        launch=[exe,f"+MOTHER={folder/'mother.mem'}",f"+LOCAL={folder/'local.mem'}",
                f"+MWORDS={len(mother)//16}",f"+LWORDS={len(local)//16}",f"+ACTIONS={folder/'actions.mem'}",
                f"+INIT={len(initial)}",f"+SEEDS={sw}",f"+READS={rw}",f"+RUNS={runs}",
                f"+STALL={stall}",f"+STATUSES={statuses:016x}",*flags]
        log=common.run(launch,out,env,folder/"run.log")
        assert f"PASS JC jobs={runs}" in log
        result=audit(log,case,status)
        results.append(dict(case=name,jobs=result,command=list(map(str,launch)),
                            sha256={p.name:common.sha(p.read_bytes()) for p in sorted(folder.iterdir())}))
        print(name,"PASS",flush=True)
    report=dict(schema=f"control-{stage.lower()}-r73/0.1",abi=profile["abi"],topology=profile["topology"],
                cases=results,compile_command=list(map(str,cmd)),compile_log_sha256=common.sha(compile_log.read_bytes()),
                python=sys.version,verilator=common.run([args.verilator,"--version"],out,env).strip())
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"PASS {stage} {len(results)} RTL scenarios",flush=True)
