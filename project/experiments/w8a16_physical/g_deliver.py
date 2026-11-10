"""Join exact-source independent gates and deliver one independently qualified native G32 or E32 AP64 leaf."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from native import check as check_native, sha

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"project/experiments/block_v2"))
from qualify import source
from pin_contract import rectangles


def accepted(folder, top="g_s32"):
    receipt = json.loads((folder/"receipt.json").read_text())
    assert receipt["passed"]
    report = json.loads((folder/"delivery.json").read_text())
    assert sha(folder/"delivery.json") == receipt["outputs"]["delivery.json"]
    assert report["passed"] and report["native_leaf_accepted"] and report["top"] == top
    for row in report["final_files"].values():
        assert sha(row["path"]) == row["sha256"]
    for row in report["gate_receipts"].values():
        assert sha(row["path"]) == row["sha256"]
        assert sha(row["report_path"]) == row["report_sha256"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--function", type=Path, required=True)
    parser.add_argument("--formal", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--top", choices=("g_s32", "e_s32_ap64"), default="g_s32")
    args = parser.parse_args()
    native = check_native()
    assert len(os.sched_getaffinity(0)) in {10,12}
    folder, _, flow, results = source(args.source)
    assert flow["top"] == args.top
    g = args.top == "g_s32"
    kind, provider, bits = ("G", "G32_SILU", 204) if g else ("E", "E32_POINTWISE_AP64", 158)
    summary = json.loads((args.audit/"audit-summary.json").read_text())
    assert summary["passed"] and Path(summary["sealed_source"]) == folder
    assert summary["final_odb_sha256"] == sha(results/"6_final.odb")
    args.out.mkdir(parents=True, exist_ok=False)
    receipt = dict(passed=False, commands=[], start_unix=time.time())
    def run(command, log):
        command = list(map(str, command))
        start = time.time()
        with (args.out/log).open("w") as stream:
            result = subprocess.run(command, cwd=args.out, stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT)
        receipt["commands"].append(dict(command=command,log=log,sha256=sha(args.out/log),
            returncode=result.returncode,seconds=time.time()-start))
        assert result.returncode == 0
    try:
        gate_locations = {"physical":(args.audit/"physical","five-macro-physical.json"),
            "drc":(args.audit/"drc","drc.json"),"density":(args.audit/"density","occupancy.json"),
            "function":(args.function,"final-function.json"),"formal":(args.formal,"formal.json")}
        proofs, gates = {}, {}
        source_sha = sha(folder/"receipt.json")
        for name,(location,filename) in gate_locations.items():
            r = json.loads((location/"receipt.json").read_text())
            assert r["passed"] and sha(location/filename) == r["outputs"][filename]
            p = json.loads((location/filename).read_text())
            if name != "density":
                assert p["passed"] and p["source_receipt_sha256"] == source_sha
            proofs[name] = p
            gates[name] = dict(path=str(location/"receipt.json"),sha256=sha(location/"receipt.json"),
                report_path=str(location/filename),report_sha256=sha(location/filename))
        assert all(proofs["physical"]["checks"].values())
        assert not proofs["drc"]["native_report"] and proofs["drc"]["full_deck"]["total_items"] == 0
        assert proofs["drc"]["final_odb_sha256"] == sha(results/"6_final.odb")
        assert proofs["function"]["final_odb_sha256"] == sha(results/"6_final.odb")
        assert proofs["formal"]["final_odb_sha256"] == sha(results/"6_final.odb")
        if g:
            assert len(proofs["function"]["runs"]) == 9 and proofs["function"]["oracle"]["actual_model_packets"] == 2048
        else:
            assert len(proofs["function"]["runs"]) == 6 and proofs["function"]["bank_sha256"] == (
                "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7")
        assert proofs["formal"]["strict_native_lec"]["passed"] and all(proofs["formal"]["strict_native_lec"]["checks"].values())
        assert proofs["formal"]["function_receipt_sha256"] == gates["function"]["sha256"]
        baseline = json.loads(Path(__file__).with_name("baseline.json").read_text())["macros"][kind]
        density = proofs["density"]
        assert density["active_outline_ratio"] >= baseline["occupied_outline_ratio"]
        assert density["active_core_ratio"] >= baseline["occupied_core_ratio"]
        plan = json.loads((folder/"pins.json").read_text())
        expected, _ = rectangles(plan,(folder/"pins.tcl").read_text(),2000)
        observed = {}
        for line in (args.audit/"physical/physical-pins.tsv").read_text().splitlines():
            name,layer,*coords=line.split("\t")
            assert name not in observed
            observed[name]=(layer,list(map(int,coords)))
        assert expected == observed and len(observed) == bits
        pins = [dict(pin=name,layer=layer,box_dbu=box) for name,(layer,box) in observed.items()]
        assert all(row["layer"] == "metal10" and row["box_dbu"][2]-row["box_dbu"][0] ==
                   row["box_dbu"][3]-row["box_dbu"][1] == 4000 for row in pins)
        (args.out/"pins.json").write_text(json.dumps(dict(dbu_per_um=2000,pins=pins),indent=2)+"\n")
        gds = Path(proofs["drc"]["original_gds"]["path"])
        assert sha(gds) == proofs["drc"]["original_gds"]["sha256"]
        files = {}
        for path in [results/("6_final."+ext) for ext in ["v","sdc","def","odb","spef"]]+[gds]:
            target=args.out/path.name
            shutil.copyfile(path,target)
            assert sha(target) == sha(path)
            files[target.name]=dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size)
        render = "import pya\nview=pya.LayoutView()\nview.load_layout("+repr(str(args.out/"6_final.gds"))+",0)\nview.max_hier()\nview.add_missing_layers()\nview.zoom_fit()\nview.save_image("+repr(str(args.out/"layout.png"))+",1600,1600)\n"
        (args.out/"render.py").write_text(render)
        run(["env","QT_QPA_PLATFORM=offscreen","klayout","-z","-r",args.out/"render.py"],"render.log")
        assert (args.out/"layout.png").stat().st_size>1000
        report = dict(passed=True,native_leaf_accepted=True,top=args.top,macro=kind,provider=provider,
            implementation_count=1,source_receipt_sha256=source_sha,gate_receipts=gates,
            final_files=files,pins=dict(path=str(args.out/"pins.json"),sha256=sha(args.out/"pins.json"),signal_bits=bits),
            image=dict(path=str(args.out/"layout.png"),sha256=sha(args.out/"layout.png")),
            die_um=flow["die_um"],density=density,active_area_um2=density["active_area_um2"],
            active_area_including_antenna_um2=proofs["physical"]["active_area_um2"],
            physical_only_area_um2=proofs["physical"]["physical_only_area_um2"],
            timing=proofs["physical"]["timing"]["timed_endpoints"],native_anchors=native,
            native_routing_layers=["metal"+str(i) for i in range(1,11)],
            finite_full_escape_qualified=False,hierarchical_lib_qualified=False,m11_m12_system_qualified=False,
            frontend_physically_qualified=False,
            scope=("P-only S32/Q16 SiLU/gated-SiLU" if g else "E32 pointwise AP64, without legacy E service replacement")+
            " native TT300MHz M1-M10 leaf, exact-source physical/density/full DRC/function/strict LEC gates. LC frontend, hierarchical timing model and product M11/M12 routes remain separate.")
        (args.out/"delivery.json").write_text(json.dumps(report,indent=2)+"\n")
        receipt["passed"]=True
    finally:
        receipt["end_unix"]=time.time()
        receipt["outputs"]={p.relative_to(args.out).as_posix():sha(p) for p in args.out.rglob("*") if p.is_file()}
        (args.out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")


if __name__ == "__main__":
    main()
