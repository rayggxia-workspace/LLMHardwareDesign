"""Strict native synthesis-to-actual-ODB G32 equivalence under original limits."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from native import check as check_native, sha, LIB

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"project/experiments/block_v2"))
from qualify import source
from native_logic_projection import export
from native_formal import fixture, inspect
from native_projection_control import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--function", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check_native()
    assert len(os.sched_getaffinity(0)) in {10, 12}
    folder, _, flow, results = source(args.source)
    assert flow["top"] == "g_s32"
    function_receipt = json.loads((args.function/"receipt.json").read_text())
    assert function_receipt["passed"]
    function = json.loads((args.function/"final-function.json").read_text())
    assert function["passed"] and function["source_receipt_sha256"] == sha(folder/"receipt.json")
    view = function["full_final_netlist"]
    actual = Path(view["full_view"])
    assert sha(actual) == view["full_view_sha256"]
    assert function["final_odb_sha256"] == sha(results/"6_final.odb")
    args.out.mkdir(parents=True, exist_ok=False)
    receipt = dict(passed=False, commands=[], source_receipt_sha256=sha(folder/"receipt.json"), start_unix=time.time())
    def run(command, log):
        command = list(map(str, command))
        start = time.time()
        with (args.out/log).open("w") as stream:
            process = subprocess.run(command, cwd=args.out, stdout=stream, stderr=subprocess.STDOUT)
        receipt["commands"].append(dict(command=command, log=log, sha256=sha(args.out/log),
            returncode=process.returncode, seconds=time.time()-start))
        assert process.returncode == 0, (log, process.returncode)
    try:
        control = args.out/"controls"
        (control/"lec").mkdir(parents=True)
        fixture(ROOT, control/"lec", run)
        for polarity in [0, 1]:
            target = control/str(polarity)
            target.mkdir()
            verify(ROOT, target, 1, lambda command, log: run(command, f"control-{polarity}-"+log), polarity)
        before, before_proof = export(ROOT, args.out, run, results/"1_synth_lec.v", LIB,
            "g_s32", "before", constant_functions=True)
        after, after_proof = export(ROOT, args.out, run, actual, LIB, "g_s32", "after", constant_functions=True)
        assert before_proof["removed_count"] == 0 and after_proof["removed_count"] > 0
        config = "format: verilog\ninput_paths:\n  - "+str(before)+"\n  - "+str(after)+"\nliberty_files:\n - "+str(LIB)+"\nlog_file: "+str(args.out/"kepler.log")+"\n"
        (args.out/"kepler.yml").write_text(config)
        binary = Path("/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal")
        run([binary, "--config", args.out/"kepler.yml"], "formal.log")
        strict = inspect((args.out/"kepler.log").read_text())
        report = dict(passed=strict["passed"], strict_native_lec=strict, before=before_proof, after=after_proof,
            source_receipt_sha256=sha(folder/"receipt.json"), function_receipt_sha256=sha(args.function/"receipt.json"),
            final_odb_sha256=sha(results/"6_final.odb"), log_sha256=sha(args.out/"kepler.log"),
            binary_sha256=sha(binary), library_sha256=sha(LIB),
            scope="Original strict all-boundary native LEC; no valid-only, data slicing or constant-state waivers")
        (args.out/"formal.json").write_text(json.dumps(report, indent=2)+"\n")
        assert report["passed"]
        receipt["passed"] = True
    finally:
        receipt["end_unix"] = time.time()
        receipt["outputs"] = {p.relative_to(args.out).as_posix(): sha(p) for p in args.out.rglob("*") if p.is_file()}
        (args.out/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    main()
