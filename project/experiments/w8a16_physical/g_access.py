"""Actual final-ODB/GDS all-bit escape, unchanged research rules and native leaf."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from native import check as check_native, sha
from g_deliver import accepted, ROOT
from profile_sources import verify
import g_geometry
import g_escape


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    native=check_native()
    profiles=verify()
    cpus=len(os.sched_getaffinity(0))
    assert cpus in (10,12)
    # The old geometry helper takes an own-root advisory lock at parents[2].
    # Require this nesting rather than writing a lock into a shared parent.
    assert args.out.parent.name=="tasks" and args.out.parent.parent.name.startswith("issue-250-g-physical-")
    args.out.mkdir(parents=True,exist_ok=False)
    index=accepted(args.delivery)
    original={str(row["path"]):row["sha256"] for row in index["final_files"].values()}
    receipts={}
    def stage(name,operation):
        out=args.out/name
        out.mkdir()
        receipt=dict(passed=False,commands=[],start_unix=time.time(),native_anchors=native,
            profiles=profiles,delivery_receipt_sha256=sha(args.delivery/"receipt.json"))
        def run(command,log):
            command=list(map(str,command))
            start=time.time()
            with(out/log).open("w")as stream:
                result=subprocess.run(command,cwd=out,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
            receipt["commands"].append(dict(command=command,log=log,sha256=sha(out/log),
                returncode=result.returncode,seconds=time.time()-start))
            assert result.returncode==0,(log,result.returncode)
        try:
            operation(out,run)
            receipt["passed"]=True
        finally:
            receipt["end_unix"]=time.time()
            receipt["outputs"]={p.relative_to(out).as_posix():sha(p) for p in out.rglob("*")if p.is_file()}
            (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
            receipts[name]=dict(path=str(out/"receipt.json"),sha256=sha(out/"receipt.json"),passed=receipt["passed"])
    def geometry(out,run):
        def selected(root,target,kind):
            assert kind=="g"
            fresh=accepted(args.delivery)
            return fresh,Path(fresh["final_files"]["6_final.odb"]["path"]),dict(
                delivery_receipt_path=str(args.delivery/"receipt.json"),delivery_receipt_sha256=sha(args.delivery/"receipt.json"),
                delivery_report_sha256=sha(args.delivery/"delivery.json")),fresh["pins"]["signal_bits"],fresh["die_um"]
        g_geometry.export(ROOT,out,cpus,run,"g",selected=selected,
            technology_name="technology-2um-v1.json",allow_zero_enclosure=True)
    stage("geometry",geometry)
    stage("escape",lambda out,run:g_escape.implement(ROOT,out,cpus,run,"g",args.delivery,args.out/"geometry",args.source))
    assert all(sha(path)==digest for path,digest in original.items())
    escape=json.loads((args.out/"escape/revision300-escape.json").read_text())
    assert escape["passed"] and escape["all_signal_bits"]==escape["simultaneous_connected_bits"]==204
    report=dict(passed=True,top="g_s32",provider="G32_SILU",finite_full_escape_qualified=True,
        source_delivery_receipt_sha256=sha(args.delivery/"receipt.json"),native_final_files=original,
        stages=receipts,all_signal_bits=204,simultaneous_connected_bits=204,
        native_m10_same_net_intersections=escape["native_m10_same_net_intersections"],
        native_m10_obstruction_intersections=escape["native_m10_obstruction_intersections"],
        native_die_um=index["die_um"],test_footprint_um=escape["test_footprint_um"],charged_halo_um=40,
        early_rc_qualified=False,combined_300mhz_interface_timing_qualified=False,
        hierarchical_lib_qualified=False,m11_m12_system_qualified=False,
        scope="All 204 actual final ODB M10 bits, complete native geometry/OBS/PG, three DEF/ODB readbacks and joined unchanged native GDS. Same uncalibrated 2um demo rules, full footprint charged; no product route/RC or manufacturing claim.")
    (args.out/"access.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


if __name__=="__main__":
    main()
