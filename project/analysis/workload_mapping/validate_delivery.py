"""Complete offline checks and fresh-process replay from an independent source copy.

No source acquisition is performed here. Supply pinned local original assets.
Runtime logs/paths/timestamps stay separate from deterministic science.json.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from .core import canonical, read_json, require
from .cli import new_output, output_build, code_hashes, sha, write_json
from .v2_bridge import accept_fixed, UPSTREAM

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PACKAGES=(HERE,HERE.parent/"llm_resources",HERE.parent/"block_v2_offline")
BASE="a5ff0c5af973ffeafa441712cd3f6e491da5a2fd"


def run_delivery(output,reference_root,allow_dirty=False):
    out=new_output(REPO,output)
    logs=out/"logs"
    logs.mkdir()
    tmp=out/"tmp"
    tmp.mkdir()
    reference_root=Path(reference_root).resolve(strict=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",GIT_NO_LAZY_FETCH="1",TMPDIR=str(tmp),TEMP=str(tmp),TMP=str(tmp),
             WORKLOAD_ASSET_ROOT=str(reference_root))
    commands=[]
    def execute(label,args,cwd=REPO,expected=0,environment=None):
        done=subprocess.run(args,cwd=cwd,env=environment or env,capture_output=True)
        (logs/(label+".stdout")).write_bytes(done.stdout)
        (logs/(label+".stderr")).write_bytes(done.stderr)
        text=(done.stdout+done.stderr).decode("utf8",errors="replace")
        counts=re.search(r"Ran (\d+) tests?",text)
        skipped=re.search(r"skipped=(\d+)",text)
        record={"label":label,"argv":list(map(str,args)),"exit_code":done.returncode,"expected_exit":expected,
                "tests":int(counts[1]) if counts else None,"skipped":int(skipped[1]) if skipped else 0,
                "stdout_sha256":hashlib.sha256(done.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(done.stderr).hexdigest()}
        commands.append(record)
        require(done.returncode==expected,label+": unexpected exit "+str(done.returncode)+"; see saved logs")
        if counts:
            require(record["skipped"]==0,label+": real-source tests were skipped")
        return done
    fixed_paths=sorted(p for root in PACKAGES[1:] for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    fixed_before={p.relative_to(REPO).as_posix():sha(p) for p in fixed_paths}
    source_before=code_hashes()
    commit=execute("source-commit",["git","rev-parse","HEAD"]).stdout.decode().strip()
    dirty=execute("source-status",["git","status","--porcelain","--untracked-files=all","--","project/analysis/workload_mapping"]).stdout.decode().strip()
    require(allow_dirty or not dirty,"freeze source in a commit before final qualification; --allow-dirty is development only")
    try:
        execute("management",[sys.executable,"-B","scripts/check_project.py"])
        for name in ("block_v2_offline","llm_resources","workload_mapping"):
            execute("tests-"+name,[sys.executable,"-B","-m","unittest","discover","-s","project/analysis/"+name,"-v"])
        originals=out/"original-replays"
        originals.mkdir()
        for name in ("graph1_reduce_rq","graph2_state_commit"):
            execute("original-"+name,[sys.executable,"-B",str(UPSTREAM/"replay.py"),str(UPSTREAM/"fixtures"/(name+".input.json")),
                "--expected",str(UPSTREAM/"fixtures"/(name+".expected.json")),"--output",str(originals/(name+".json"))])
        from .examples import minimal,reuse,state_feedback,attention,blocks_replacement,alias_copy_transport
        builders={"minimal":minimal,"reuse":reuse,"state_feedback":state_feedback,
                  "attention_tiny":lambda:attention(True),"qwen_config":attention,
                  "blocks_replacement":blocks_replacement,"alias_copy_transport":alias_copy_transport}
        first=out/"first"
        first.mkdir()
        cases={}
        for name,builder in builders.items():
            graph,blocks=builder()
            target=new_output(first,name)
            result=output_build(graph,blocks,target)
            cases[name]={"result":result,"directory":target,"semantics":None}
        for name,scenario in (("graph1_reduce_rq","normal"),("graph2_state_commit","normal"),("graph2_state_commit","failure_retry")):
            graph,blocks,semantics,actual=accept_fixed(UPSTREAM/"fixtures"/(name+".input.json"),UPSTREAM/"fixtures"/(name+".expected.json"),scenario)
            label=name+"-"+scenario
            target=new_output(first,label)
            result=output_build(graph,blocks,target,semantics)
            expected=read_json(UPSTREAM/"fixtures"/(name+".expected.json"))
            oracle=expected if name=="graph1_reduce_rq" else expected[scenario]
            communications=result["mapping_request"]["communication"]
            for observed,wanted in ((len(communications),oracle["runtime_traffic"]["messages"]),
                (sum(t["container_bytes"]*t["messages"] for t in communications),oracle["runtime_traffic"]["logical_payload_bytes"]),
                (sum(t["transport"]["wire_bytes"]*t["messages"] for t in communications),oracle["runtime_traffic"]["physical_bytes"]),
                (sum(t["transport"]["ideal_link_cycles"]*t["messages"] for t in communications),oracle["runtime_traffic"]["link_beats"])):
                require(observed==wanted,"generic communication differs from independent expected")
            require(result["mapping_request"]["storage"]["peak_bytes"]==expected["storage"]["peak_reserved_bytes"],"generic static reservation differs from expected")
            domain_total=sum(d["bytes"] for d in result["mapping_request"]["semantic_report"]["domain_peak_bytes"])
            require(domain_total==expected["storage"]["total_reserved_bytes"],"private/bank/FIFO reservation mismatch")
            cases[label]={"result":result,"directory":target,"semantics":semantics,"upstream_actual_sha256":hashlib.sha256(canonical(actual)).hexdigest(),
                          "fixed_oracle_match":True,"upstream_runtime_traffic":oracle["runtime_traffic"],
                          "initial_setup_traffic":{k:v for k,v in actual.items() if "setup" in k}}
        # Re-run with exactly the same frozen source bytes, from another cwd.
        frozen=out/"frozen-source"
        frozen.mkdir()
        for root in PACKAGES:
            for p in root.rglob("*"):
                if p.is_file() and p.suffix in (".py",".json") and "__pycache__" not in p.parts:
                    dst=frozen/p.relative_to(REPO)
                    dst.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(p,dst)
        replay=out/"independent-replay"
        replay.mkdir()
        frozen_env=dict(env,GIT_CEILING_DIRECTORIES=str(out),PYTHONPATH=str(frozen))
        science={}
        for name,case in cases.items():
            original=case["directory"]
            second=replay/name
            execute("replay-"+name,[sys.executable,"-B","-m","project.analysis.workload_mapping","replay",
                "--bundle",str(original),"--root",str(replay),"--output-dir",str(second)],cwd=frozen,environment=frozen_env)
            selected=("mapping_request.json","resource_input.json","resource_report.json","summary.json")
            equality={f:sha(original/f)==sha(second/f) for f in selected}
            require(all(equality.values()),"independent scientific SHA mismatch")
            m=case["result"]["mapping_request"]
            science[name]={"scientific_sha256":{f:sha(original/f) for f in selected},"replay_equal":equality,
                "logical":case["result"]["summary"]["logical"],"messages":sum(c["messages"] for c in m["communication"]),
                "hop_summed_wire_bytes":sum(c["transport"]["hop_summed_wire_bytes_per_step"] for c in m["communication"] if c["transport"] and "hop_summed_wire_bytes_per_step" in c["transport"]),
                "peak_reserved_bytes":m["storage"]["peak_bytes"],"unique_weight_elements":m["storage"]["unique_weight_elements"],
                "upstream_actual_sha256":case.get("upstream_actual_sha256"),"physical":case["result"]["summary"]["physical"],
                "fixed_oracle_match":case.get("fixed_oracle_match"),
                "upstream_runtime_traffic":case.get("upstream_runtime_traffic"),
                "initial_setup_traffic":case.get("initial_setup_traffic"),
                "domain_peak_bytes":m.get("semantic_report",{}).get("domain_peak_bytes"),
                "semantic_transitions":m.get("semantic_report",{}).get("transitions"),
                "bank_accesses":m.get("semantic_report",{}).get("bank_accesses")}
        script=HERE/"assets/replay_reference_import.py"
        execute("reference-first",[sys.executable,"-B",str(script),"--reference-root",str(reference_root),"--output",str(out/"reference-first")])
        execute("reference-independent",[sys.executable,"-B",str(frozen/script.relative_to(REPO)),"--reference-root",str(reference_root),"--output",str(frozen/"reference-independent")],cwd=frozen,environment=frozen_env)
        b_first=out/"reference-first/summary.json"
        b_second=frozen/"reference-independent/summary.json"
        require(sha(b_first)==sha(b_second),"reference import replay mismatch")
        binding=out/"binding"
        execute("binding-physical-blocked",[sys.executable,"-B","-m","project.analysis.workload_mapping","bind",
            "--assets-dir",str(reference_root),"--binding",str(HERE/"assets/reference_binding.example.json"),"--physical",
            "--root",str(out),"--output-dir",str(binding)],expected=3)
        execute("binding-verify",[sys.executable,"-B","-m","project.analysis.workload_mapping","verify","--bundle",str(binding),"--reference-root",str(reference_root)])
        execute("binding-replay",[sys.executable,"-B","-m","project.analysis.workload_mapping","replay","--bundle",str(binding),
            "--reference-root",str(reference_root),"--root",str(replay),"--output-dir",str(replay/"binding")],cwd=frozen,environment=frozen_env)
        require(sha(binding/"summary.json")==sha(replay/"binding/summary.json"),"binding scientific replay mismatch")
        execute("fixed-dependency-diff",["git","diff","--exit-code",BASE,"--","project/analysis/llm_resources","project/analysis/block_v2_offline","docs/BLOCK_V2_FIELD_MAPPING.md"])
        execute("whitespace",["git","diff","--check"])
        require(code_hashes()==source_before,"source changed during run")
        fixed_after={p.relative_to(REPO).as_posix():sha(p) for p in fixed_paths}
        require(fixed_before==fixed_after,"fixed fixture/expected/source bytes changed")
        write_json(out/"science.json",{"schema":"workload-delivery-science/1","cases":science,
            "reference_summary_sha256":sha(b_first),"binding_summary_sha256":sha(binding/"summary.json"),
            "reference_replay_equal":True,"A":"pass","B":"pass selected reference import/ports; protocol unverified","C":"blocked"})
        receipt={"schema":"workload-delivery-receipt/1","status":"pass","source_commit":commit,
            "source_clean":not bool(dirty),"frozen_source_sha256":source_before,"fixed_inputs_sha256":fixed_after,
            "fixed_inputs_unchanged":True,"independent_copy_and_process_replay":True,
            "commands":commands,"test_count":sum(r["tests"] or 0 for r in commands),"skipped":0,
            "science_sha256":sha(out/"science.json"),"server_access":False,
            "scope":"selected static logical conversion and actual old reference assets; no physical qualification"}
        write_json(out/"receipt.json",receipt)
        write_json(out/"runtime.json",{"output":str(out),"utc_epoch_seconds":time.time(),"python":sys.version,"development_allow_dirty":allow_dirty})
        print(json.dumps({"status":"pass","tests":receipt["test_count"],"independent_replays":len(cases),"source_clean":receipt["source_clean"],"science_sha256":receipt["science_sha256"],"C":"blocked"}))
        return receipt
    except Exception as exc:
        write_json(out/"failure.json",{"status":"fail","error":str(exc),"commands":commands,"source_commit":commit})
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--reference-root",default=str(REPO/".local/dependencies/reference_assets"))
    p.add_argument("--allow-dirty",action="store_true")
    a=p.parse_args()
    run_delivery(a.output_dir,a.reference_root,a.allow_dirty)


if __name__=="__main__":
    main()
