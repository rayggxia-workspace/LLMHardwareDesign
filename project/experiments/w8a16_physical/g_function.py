"""Actual final-ODB G32 netlist, protection loads retained, exact tensor replay."""
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
from native_signal_view import export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check_native()
    cpus = len(os.sched_getaffinity(0))
    assert cpus in {10, 12}
    folder, original, flow, results = source(args.source)
    assert flow["top"] == "g_s32"
    args.out.mkdir(parents=True, exist_ok=False)
    receipt = dict(passed=False, source_receipt_sha256=sha(folder/"receipt.json"), commands=[], start_unix=time.time())
    def run(command, log):
        command = list(map(str, command))
        start = time.time()
        with (args.out/log).open("w") as stream:
            process = subprocess.run(command, cwd=args.out, stdout=stream, stderr=subprocess.STDOUT)
        receipt["commands"].append(dict(command=command, log=log, sha256=sha(args.out/log),
            returncode=process.returncode, seconds=time.time()-start))
        assert process.returncode == 0, (log, process.returncode)
    try:
        netlist, proof = export(ROOT, args.out, run, folder, original, results, "g_s32", LIB)
        (args.out/"cells.ys").write_text(f"read_liberty -ignore_miss_func -ignore_miss_dir {LIB}\nwrite_verilog -noattr cells.v\n")
        run(["yosys", "-s", args.out/"cells.ys"], "cells.log")
        run(["python3", ROOT/"project/experiments/w8a16_g/make_vectors.py", "--out", args.out], "oracle.log")
        vlt = "/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator"
        # Same main policy for generated Liberty cell models. Production RTL
        # has its separate strict --Wall gate; assertions remain enabled here.
        run([vlt, "--binary", "--timing", "--assert", "--timescale-override", "1ns/1ps", "-Wno-fatal",
             "--x-initial", "unique", "--x-assign", "unique", "--top-module", "test_g_s32", "-j", cpus,
             "--Mdir", args.out/"obj", ROOT/"project/experiments/w8a16_g/test_g_s32.sv", netlist, args.out/"cells.v"], "build.log")
        runs = []
        for mode in range(3):
            for initial, seed in [(1,143), (2,143), (2,144)]:
                log = f"mode{mode}-{initial}-{seed}.log"
                run([args.out/"obj/Vtest_g_s32", "+vectors="+str(args.out/"vectors.txt"), f"+mode={mode}",
                     f"+verilator+rand+reset+{initial}", f"+verilator+seed+{seed}"], log)
                text = (args.out/log).read_text()
                assert "G_S32_PASS" in text and "%Error" not in text
                runs.append(dict(mode=mode, initial=initial, seed=seed, log=log, sha256=sha(args.out/log)))
        report = dict(passed=True, source_receipt_sha256=sha(folder/"receipt.json"), full_final_netlist=proof,
            final_odb_sha256=sha(results/"6_final.odb"), runs=runs,
            oracle=json.loads((args.out/"oracle.json").read_text()),
            scope="Actual physical ODB signal-bearing netlist including protection loads; 8048 packets with actual four-FFN tensors, three initial states, stall/reset modes")
        assert report["oracle"]["actual_model_packets"] == 2048
        (args.out/"final-function.json").write_text(json.dumps(report, indent=2)+"\n")
        receipt["passed"] = True
    finally:
        receipt["end_unix"] = time.time()
        receipt["outputs"] = {p.relative_to(args.out).as_posix(): sha(p) for p in args.out.rglob("*") if p.is_file()}
        (args.out/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    main()
