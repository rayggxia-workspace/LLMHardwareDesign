#!/usr/bin/env python3
"""Consolidate actually measured input records; never infer stage completion."""
import argparse
import hashlib
import json
from pathlib import Path

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for x in iter(lambda:f.read(1048576),b""):
            h.update(x)
    return h.hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

def record(path):
    p=Path(path)
    return {"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--task-root",required=True)
    p.add_argument("--config",required=True)
    p.add_argument("--native",action="append",required=True,help="case_id=completed native run")
    p.add_argument("--output",required=True,help="new directory for consolidated immutable records")
    a=p.parse_args()
    root=Path(a.task_root).resolve(strict=True)
    allowed=Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    if allowed not in root.parents:
        raise ValueError("Task root outside allowed subtree")
    out=Path(a.output)
    if out.exists() or out.is_symlink() or root not in out.parent.resolve(strict=True).parents:
        raise ValueError("Output must be new and inside task root")
    cfg=load(a.config)
    primary={x["id"]:x for x in cfg["cases"] if x["role"]=="primary"}
    paths={}
    for entry in a.native:
        k,v=entry.split("=",1)
        if k in paths:
            raise ValueError("Duplicate case input")
        paths[k]=Path(v).resolve(strict=True)
    if set(paths)!=set(primary):
        raise ValueError("Must provide exactly all configured primary Block inputs")
    catalog=[]; manifest=[]; native_evidence=[]
    reserved=set(cfg["custom_routing_levels"])
    for cid in sorted(paths):
        run=paths[cid]
        execution=load(run/"execution.json")
        if execution["status"]!="pass_inventory_only":
            raise ValueError("Native inventory did not complete: "+cid)
        summary=load(run/"summary.json")
        if summary["case_id"]!=cid or summary["native"]["block"]!=primary[cid]["expected_master"]:
            raise ValueError("Case identity mismatch")
        for name, rec in execution["artifacts"].items():
            path=run/name
            if not path.is_file() or sha(path)!=rec["sha256"]:
                raise ValueError("Native artifact changed: "+str(path))
        levels={x["name"]:int(x["routing_level"]) for x in summary["layers"]}
        counts=summary["shape_counts"]
        used=[x for x in counts if levels.get(x["layer"],0) in reserved and x["kind"]!="BLOCK_OBS"]
        pin_layers=sorted({x["layer"] for x in counts if x["kind"]=="BPIN"})
        bbox=summary["die_bbox_dbu"]; dbu=summary["dbu_per_um"]
        row={
            "id":cid,"master":summary["native"]["block"],"candidate_version":cfg["case_version"],
            "source_commit":summary["source_commit"],"parameters":summary["parameters"],
            "size_um":[(bbox[2]-bbox[0])/dbu,(bbox[3]-bbox[1])/dbu],
            "internal_instances":summary["counts"]["instances"],
            "memory_macro_types":[m for m in summary["masters"] if m["master_type"]=="BLOCK"],
            "logical_port_groups":summary["port_groups"],"signal_port_bits":summary["counts"]["signal_port_bits"],
            "pin_layers":pin_layers,"clock_constraints":summary["clock_constraints"],
            "layer_definitions":summary["layers"],"custom_layer_existing_geometry_counts":used,
            "custom_layer_existing_net_counts":summary["upper_layer_occupancy"]["net_counts"],
            "geometry_and_pin_index":str(run/"native"),"native_execution":record(run/"execution.json"),
            "native_summary":record(run/"summary.json"),
            "inherited_metrics":summary.get("inherited_metrics",{}),
            "inherited_metrics_source":execution.get("inherited_metrics_source"),
            "validation":{"native_input_inventory":"pass","migration_to_M1_M8":"not_executed",
                "M8_fixed_access":"not_executed","full_top_integration":"not_executed",
                "new_DRC":"not_executed","new_RC_STA":"not_executed"},
            "limits":["Port bit count is not per-cycle bandwidth.",
                "Existing run metrics are inherited evidence, not newly run timing.",
                "Geometry inventory is not connectivity or DRC signoff.",
                "Memory macros here are case research models, not production SRAM qualification."]}
        catalog.append(row)
        native_evidence.append({"case":cid,"job":execution["scheduler_job_id"],
            "source_adapter":execution["tools"]["adapter"],"summary":record(run/"summary.json")})
        for role,rec in execution["inputs"].items():
            manifest.append(dict(rec,case=cid,role=role,measured_by=str(run/"execution.json"),
                checksum_scope="Actual input SHA measured by successful scheduler inventory; not rehashed by catalog"))
    rtl_path=root/"inputs/rtl_inventory.json"
    baseline_path=root/"inputs/baseline_evidence.json"
    rtl=load(rtl_path)
    for cid,build in rtl["build_inputs"].items():
        for rec in build.get("ordered_source_files",[]):
            manifest.append(dict(rec,case=cid,role="ordered_rtl",
                measured_by=str(rtl_path),checksum_scope="Actual selected source SHA and historical baseline identity check"))
    result={"schema_version":1,"status":"measured_input_inventory_not_stage_acceptance",
        "config":record(a.config),"sources":rtl["source_versions"],"inputs":manifest,
        "native_evidence":native_evidence,"rtl_inventory":record(rtl_path),
        "baseline_evidence":record(baseline_path),"coverage_map":record(root/"deliverables/coverage_map.csv"),
        "remaining":["Official selected-top complete hierarchy/state/memory ownership",
                     "Whole-top integration and functional comparison","Physical migration/base/routing stages"]}
    out.mkdir()
    for name,value in [("input_manifest.json",result),("block_catalog.json",{
        "schema_version":1,"status":"measured_candidates_not_frozen_base","primary":catalog,
        "alternatives":[x for x in cfg["cases"] if x["role"]!="primary"],
        "formal_block_specification":"not supplied; these are case implementations"})]:
        with (out/name).open("x") as f:
            json.dump(value,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":"catalog_created_not_stage_pass","output":str(out),"primary_blocks":len(catalog)}))

if __name__=="__main__":
    main()
