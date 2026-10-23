"""Read native track patterns and pin access inputs; does not generate access wires."""
import argparse, importlib.util, json, os, shutil, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("access_inventory", HERE/"native_inventory.py")
inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory-run",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if not os.getenv("SLURM_JOB_ID"):raise RuntimeError("Scheduler allocation required")
    source=Path(a.inventory_run).resolve(strict=True)
    prior=inv.read_json(source/"execution.json")
    if prior.get("status")!="pass_inventory_only":raise ValueError("Expected closed native inventory")
    odb=prior["inputs"]["odb"]
    if inv.digest(odb["path"])!=odb["sha256"]:raise ValueError("Original ODB changed")
    tool=shutil.which("openroad")
    if not tool or inv.digest(tool)!=prior["tools"]["openroad"]["sha256"]:
        raise ValueError("OpenROAD binary differs from inventory")
    out=inv.safe_new(a.output)
    script=HERE/"access_probe.tcl"
    result={"status":"running","scheduler_job_id":os.getenv("SLURM_JOB_ID"),
            "source_receipt":inv.source_record(source/"execution.json"),
            "odb":odb,"tool":inv.source_record(tool),"script":inv.source_record(script),
            "source":inv.source_record(__file__),
            "scope":"Read-only native tracks/pins/symmetry probe; no access route, geometry or timing acceptance"}
    try:
        cmd=[tool,"-exit",str(script)]
        env=dict(os.environ,HPY_ACCESS_ODB=odb["path"])
        with (out/"native_access.log").open("x") as f:
            proc=subprocess.run(cmd,cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT)
        result["command"]=cmd;result["returncode"]=proc.returncode
        lines=(out/"native_access.log").read_text().splitlines()
        if proc.returncode or not any(x.startswith("HPY_ACCESS_PROBE_COMPLETE\t") for x in lines):
            raise RuntimeError("Native probe did not complete")
        failures=[x for x in lines if x.startswith(("TRACK_MISSING\t","TRACK_PATTERN_ERROR\t","UNSUPPORTED_"))]
        patterns=[x.split("\t") for x in lines if x.startswith("TRACK_PATTERN\t")]
        failures.extend("\t".join(x) for x in patterns if len(x)<6 or x[4]!="0")
        result["track_pattern_count"]=len(patterns)
        result["bpin_rectangle_count"]=sum(x.startswith("BPIN\t") for x in lines)
        result["unresolved"]=failures
        if inv.digest(odb["path"])!=odb["sha256"]:raise ValueError("ODB changed during probe")
        result["inputs_unchanged"]=True
        result["status"]="pass_read_only_access_inputs_only" if not failures and patterns else "blocked_native_access_inputs"
    except Exception as exc:result.update(status="fail_access_probe",error=type(exc).__name__+": "+str(exc))
    result["log"]=inv.source_record(out/"native_access.log") if (out/"native_access.log").exists() else None
    inv.write_json(out/"execution.json",result)
    print(json.dumps({"status":result["status"],"receipt":str(out/"execution.json")}))
    return 0 if result["status"]=="pass_read_only_access_inputs_only" else 1
if __name__=="__main__":raise SystemExit(main())
