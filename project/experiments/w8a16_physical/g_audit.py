"""Original independent STA/electrical/PG/DRC plus compact density for G32."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from native import check as check_native, sha, DECK

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"project/experiments/block_v2"))
import qualify
from receive import physical
from native_drc import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    native = check_native()
    cpus = len(os.sched_getaffinity(0))
    assert cpus in {10, 12}
    args.out.mkdir(parents=True, exist_ok=False)
    stage_results = {}
    def stage(name, operation):
        out = args.out/name
        out.mkdir()
        receipt = dict(passed=False, operation=name, source=str(args.source),
                       native_anchors=native, commands=[], start_unix=time.time())
        def run(command, log):
            command = list(map(str, command))
            start = time.time()
            with (out/log).open("w") as stream:
                proc = subprocess.run(command, cwd=out, stdout=stream, stderr=subprocess.STDOUT)
            receipt["commands"].append(dict(command=command, log=log, sha256=sha(out/log),
                returncode=proc.returncode, seconds=time.time()-start))
            assert proc.returncode == 0, (log, proc.returncode)
        try:
            operation(out, run)
            receipt["passed"] = True
        except Exception as error:
            receipt["error"] = repr(error)
        finally:
            receipt["end_unix"] = time.time()
            receipt["outputs"] = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()}
            (out/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
            stage_results[name] = dict(passed=receipt["passed"], receipt_sha256=sha(out/"receipt.json"),
                                       error=receipt.get("error"))
        return receipt["passed"]
    assert stage("sealed", lambda out, run: qualify.seal(args.source, out)), stage_results
    sealed = args.out/"sealed"
    selected = lambda target, kind: qualify.source(sealed)
    stage("physical", lambda out, run: physical(ROOT, out, cpus, run, "g32", selected=selected))
    _, _, flow, results = qualify.source(sealed)
    def density(out, run):
        target = out/"occupancy.json"
        run(["python3", ROOT/"project/experiments/block_v2/compact_occupancy.py", results/"6_final.odb", target], "occupancy.log")
        record = json.loads(target.read_text())
        base = json.loads(Path(__file__).with_name("baseline.json").read_text())["macros"]["G"]
        assert record["active_outline_ratio"] >= base["occupied_outline_ratio"]
        assert record["active_core_ratio"] >= base["occupied_core_ratio"]
    stage("density", density)
    def drc(out, run):
        script = out/"native-drc.tcl"
        script.write_text(f"set_thread_count {cpus}\nread_db {{{results/'6_final.odb'}}}\nwrite_def before.def\n"
            "drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 g32_whole_drc\nwrite_def after.def\n")
        run(["openroad", "-no_init", "-exit", script], "native-drc.log")
        assert sha(out/"before.def") == sha(out/"after.def")
        native_text = (out/"native-whole-drc.rpt").read_text()
        raw_results = args.source/"flow/results/nangate45/bv1_g_s32/base"
        gds = raw_results/"6_final.gds"
        if not gds.exists():
            run(["make", "-C", "/OpenROAD-flow-scripts/flow", "DESIGN_CONFIG="+str(args.source/"config.mk"),
                "WORK_HOME="+str(args.source/"flow"), f"NUM_CORES={cpus}", "do-gds"], "gds.log")
        run(["klayout", "-b", "-rd", "in_gds="+str(gds), "-rd", "report_file="+str(out/"full-deck.lyrdb"),
             "-r", DECK], "full-deck.log")
        full = summarize(out/"full-deck.lyrdb")
        record = dict(passed=not native_text.strip() and full["total_items"] == 0,
            original_gds=dict(path=str(gds), sha256=sha(gds), bytes=gds.stat().st_size),
            final_odb_sha256=sha(results/"6_final.odb"), source_def_sha256=sha(raw_results/"6_final.def"),
            native_report=native_text, full_deck=full, deck_sha256=sha(DECK), native_anchors=native,
            source_receipt_sha256=sha(sealed/"receipt.json"))
        (out/"drc.json").write_text(json.dumps(record, indent=2)+"\n")
        assert record["passed"]
    stage("drc", drc)
    report = dict(passed=all(row["passed"] for row in stage_results.values()), stages=stage_results,
        source=str(args.source), sealed_source=str(sealed), final_odb_sha256=sha(results/"6_final.odb"),
        new_macro_function_qualified=False, strict_boundary_lec_qualified=False, native_leaf_accepted=False,
        scope="Independent physical/density/DRC gates only; final netlist regression, strict LEC and delivery still required")
    (args.out/"audit-summary.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report))
    assert report["passed"]


if __name__ == "__main__":
    main()
