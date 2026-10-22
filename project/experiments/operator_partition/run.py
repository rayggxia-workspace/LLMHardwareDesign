"""Run and archive the declared boundary pilot; see README for evidence scope."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile
import numpy as np
from ledger import attention, ffn_workload, qualify

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")


def validate_model(model):
    path=HERE/model["input_file"]
    if sha(path)!=model["input_sha256"]: raise ValueError("input SHA mismatch")
    if path.suffix==".json":
        raw=json.loads(path.read_text(encoding="utf-8"))
        c=raw.get("text_config",raw)
        is_dense=model["id"].endswith("/dense")
        expected={"hidden":c["hidden_size"],
                  "intermediate":c["intermediate_size"] if is_dense else c.get("moe_intermediate_size",c.get("intermediate_size"))}
        if "query_heads" in model:
            expected.update(query_heads=c["num_attention_heads"],kv_heads=c["num_key_value_heads"],
                            head_dim=c.get("head_dim",c["hidden_size"]//c["num_attention_heads"]))
    else:
        # Parse only the public SKU's first function; never execute upstream code.
        tree=ast.parse(path.read_text(encoding="utf-8").split("def arch_args_3b")[0])
        mapping=tree.body[0].body[0].value
        c={key.value:value.value for key,value in zip(mapping.keys,mapping.values)
           if isinstance(key,ast.Constant) and isinstance(value,ast.Constant)}
        f=int(int(2*(4*c["dim"])/3)*c["ffn_dim_multiplier"])
        f=c["multiple_of"]*((f+c["multiple_of"]-1)//c["multiple_of"])
        expected=dict(hidden=c["dim"],intermediate=f,query_heads=c["n_heads"],
                      kv_heads=c["n_kv_heads"],head_dim=c["dim"]//c["n_heads"])
    for key,value in expected.items():
        if model.get(key)!=value: raise ValueError("derived model field mismatch: "+model["id"]+"/"+key)


def audit_events(events, expected):
    """Rebuild counters and simultaneous bank occupancy without Ledger calls."""
    active={}; counts=Counter(); live=Counter(matrix=0,vector=0)
    peak=Counter(matrix=0,vector=0); total=0; burst=0
    for e in events:
        n=e["multiplicity"]; kind=e["kind"]
        if kind=="alloc":
            if e["name"] in active: raise AssertionError("duplicate allocation")
            active[e["name"]]=(e["bank"],e["size"])
            live[e["bank"]]+=e["size"]
            peak[e["bank"]]=max(peak[e["bank"]],live[e["bank"]])
            total=max(total,sum(live.values()))
        elif kind=="free":
            bank,size=active.pop(e["name"])
            live[bank]-=size
        elif kind in ("load","store"):
            bank,size=active[e["name"]]
            counts["external_read" if kind=="load" else "external_write"]+=size*n
            counts[bank+("_write" if kind=="load" else "_read")]+=size*n
        elif kind=="copy":
            sb,size=active[e["source"]]; db,other=active[e["target"]]
            if size!=other or sb==db: raise AssertionError("invalid copy")
            counts[sb+"_read"]+=size*n; counts[db+"_write"]+=size*n
            counts[sb+"_to_"+db]+=size*n; burst=max(burst,size)
        elif kind=="compute":
            counts[e["bank"]+"_read"]+=e["read"]*n
            counts[e["bank"]+"_write"]+=e["write"]*n
            counts["macs"]+=e["macs"]*n
        else: raise AssertionError("unknown event")
    counts["engine_transfer_bytes"]=counts["matrix_to_vector"]+counts["vector_to_matrix"]
    counts["external_bytes"]=counts["external_read"]+counts["external_write"]
    counts["sram_access_bytes"]=sum(counts[b+"_"+o] for b in ("matrix","vector") for o in ("read","write"))
    if active or any(live.values()): raise AssertionError("live buffers at end")
    if dict(counts)!=expected["counts"]: raise AssertionError("counter mismatch")
    if dict(peak)!=expected["peak_bank_bytes"] or total!=expected["peak_total_bytes"]:
        raise AssertionError("lifetime peak mismatch")
    if burst!=expected["max_copy_burst_bytes"]: raise AssertionError("burst mismatch")


def closed_form(case, result, scalar):
    c=result["counts"]
    if case["kernel"]=="ffn":
        t,h,f=case["tokens"],case["hidden"],case["intermediate"]
        nt=(t+case["token_tile"]-1)//case["token_tile"]
        expected=(3*t*h*f,(2*t*h+3*nt*h*f)*scalar,3*t*f*scalar)
    else:
        q,k,nh,nk,d=(case[x] for x in ("queries","keys","query_heads","kv_heads","head_dim"))
        nq=(q+case["query_tile"]-1)//case["query_tile"]
        nkt=(k+case["key_tile"]-1)//case["key_tile"]
        extra=nh*q*nkt*d if case["schedule"]=="streaming" else 0
        expected=(2*nh*q*k*d,(2*nh*q*d+2*nq*nk*k*d)*scalar,(2*nh*q*k+extra)*scalar)
    actual=(c["macs"],c["external_bytes"],c["engine_transfer_bytes"])
    if expected!=actual: raise AssertionError((case,expected,actual))


def pareto_indices(rows):
    """Preserve ties. These are schedule tradeoffs, not physical Block optima."""
    keys=("external_bytes","sram_access_bytes","engine_transfer_bytes",
          "matrix_peak","vector_peak","max_copy_burst")
    vectors=[tuple(r[k] for k in keys) for r in rows]
    return [i for i,a in enumerate(vectors)
            if not any(all(bv<=av for bv,av in zip(b,a)) and any(bv<av for bv,av in zip(b,a))
                       for j,b in enumerate(vectors) if i!=j)]


def run(out):
    if out.exists(): raise ValueError("output must be a new directory; preserve previous attempts")
    source_files=sorted(p for p in HERE.rglob("*") if p.is_file() and p.suffix in (".py",".json",".txt",".md")
                        and "results" not in p.parts and "local_runs" not in p.parts and "__pycache__" not in p.parts)
    inputs={str(p.relative_to(ROOT)).replace("\\","/"):sha(p) for p in source_files}
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    status=subprocess.check_output(["git","status","--porcelain","--untracked-files=all"],cwd=ROOT,text=True)
    if status.strip(): raise ValueError("formal run requires clean source tree: "+status)
    cfg=json.loads((HERE/"experiment.json").read_text(encoding="utf-8"))
    models=json.loads((HERE/"model-cases.json").read_text(encoding="utf-8"))["cases"]
    for m in models:
        validate_model(m)
    out.mkdir(parents=True)
    rows=[]; traces=[]; qualifications=[]; b=cfg["scalar_bytes"]
    def record(case,result):
        audit_events(result["events"],result); closed_form(case,result,b)
        rid=len(rows)
        r=dict(case,case_id=rid,**result["counts"],
               matrix_peak=result["peak_bank_bytes"]["matrix"],
               vector_peak=result["peak_bank_bytes"]["vector"],
               peak_total=result["peak_total_bytes"],max_copy_burst=result["max_copy_burst_bytes"],
               persistent_external_kv_bytes=result.get("persistent_external_kv_bytes",0))
        rows.append(r)
        traces.append(dict(case_id=rid,events=result["events"]))
        for mc,vc in cfg["bank_capacity_pairs_bytes"]:
            for reserve in cfg["reserves_percent"]:
                for part in cfg["partitions"]:
                    qualifications.append(dict(case_id=rid,matrix_capacity=mc,vector_capacity=vc,
                        reserve_percent=reserve,**qualify(result,mc,vc,reserve,part)))
    for m in models:
        for tokens in cfg["tokens"]:
            token_tiles=sorted(set(min(tokens,x) for x in cfg["ffn_token_tiles"]))
            feature_tiles=sorted(set(min(m["intermediate"],x) for x in cfg["ffn_tiles"]))
            for tt in token_tiles:
                for ft in feature_tiles:
                    for s in cfg["schedules"]:
                        case=dict(model=m["id"],kernel="ffn",phase="decode" if tokens==1 else "prefill",
                                  scope=m["ffn_scope"],tokens=tokens,hidden=m["hidden"],
                                  intermediate=m["intermediate"],token_tile=tt,feature_tile=ft,schedule=s)
                        record(case,ffn_workload(tokens,m["hidden"],m["intermediate"],tt,ft,s,b))
        if "query_heads" not in m: continue
        for phase in ("prefill","decode"):
            for context in cfg["context_lengths"]:
                q=context if phase=="prefill" else 1
                for qt,kt in cfg["attention_tiles"]:
                    qt=min(q,qt);kt=min(context,kt)
                    for s in cfg["schedules"]:
                        case=dict(model=m["id"],kernel="attention",phase=phase,scope=m["attention_scope"],
                                  queries=q,keys=context,query_heads=m["query_heads"],kv_heads=m["kv_heads"],
                                  head_dim=m["head_dim"],query_tile=qt,key_tile=kt,schedule=s)
                        record(case,attention(q,context,m["query_heads"],m["kv_heads"],m["head_dim"],qt,kt,s,b))
    # Equal work and traffic in each pair; partition cannot silently add memory.
    for a,z in zip(rows[::2],rows[1::2]):
        if a["schedule"]!="materialized" or z["schedule"]!="streaming": raise AssertionError("pair order")
        for key in ("macs","external_bytes"):
            if a[key]!=z[key]: raise AssertionError("unfair paired resources")
    for a,z in zip(qualifications[::2],qualifications[1::2]):
        if a["selected_schedule_fits"]!=z["selected_schedule_fits"] or a["headroom"]!=z["headroom"]:
            raise AssertionError("join changed bank capacity")
    groups={}
    for row in rows:
        key=(row["model"],row["kernel"],row["phase"],row.get("tokens"),row.get("keys"))
        groups.setdefault(key,[]).append(row)
    fronts=[dict(workload=list(key),case_ids=[rs[i]["case_id"] for i in pareto_indices(rs)]) for key,rs in groups.items()]
    from numerical_oracles import run_checks
    numerical=run_checks()
    dump(out/"numerical.json",numerical)
    dump(out/"rows.json",rows);dump(out/"capacity.json",qualifications);dump(out/"pareto.json",fronts)
    with (out/"events.jsonl").open("w",encoding="utf-8",newline="\n") as f:
        for trace in traces: f.write(json.dumps(trace,sort_keys=True,separators=(",",":"))+"\n")
    summary=dict(schema_version=1,model_cases=len(models),schedule_cases=len(rows),
                 capacity_boundary_cases=len(qualifications),workloads=len(groups),
                 event_replay_and_closed_form_pass=len(rows),paired_schedule_checks=len(rows)//2,
                 capacity_pass=sum(x["selected_schedule_fits"] for x in qualifications),
                 capacity_fail=sum(not x["selected_schedule_fits"] for x in qualifications),
                 physical_qualified=False,full_model_run=False,scope=cfg["purpose"])
    dump(out/"summary.json",summary)
    if any(sha(ROOT/name)!=digest for name,digest in inputs.items()):
        raise RuntimeError("source/input changed during run; partial output retained, no qualified manifest")
    if subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()!=head:
        raise RuntimeError("HEAD changed during run")
    if subprocess.check_output(["git","status","--porcelain","--untracked-files=all"],cwd=ROOT,text=True).strip():
        raise RuntimeError("source tree changed during run")
    artifacts={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    dump(out/"manifest.json",dict(source_commit=head,source_status="clean",command="python project/experiments/operator_partition/run.py --out <new-directory>",
        python=sys.version,numpy=np.__version__,platform=platform.platform(),inputs=inputs,artifacts=artifacts,
        evidence_scope="analytical resource ledger and synthetic numeric kernels; no model weights, EDA, RTL, or hardware speed"))
    with zipfile.ZipFile(out/"evidence.zip","w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(out.iterdir()):
            if p.name=="evidence.zip": continue
            info=zipfile.ZipInfo(p.name,date_time=(2026,10,22,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes())
    dump(out/"archive-sha256.json",dict(file="evidence.zip",bytes=(out/"evidence.zip").stat().st_size,sha256=sha(out/"evidence.zip")))
    print(json.dumps(summary));print("archive_sha256="+sha(out/"evidence.zip"))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True,type=Path)
    run(parser.parse_args().out.resolve())
