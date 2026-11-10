"""Actual final-ODB E32 AP64 netlist with protection loads, exercised through the real four-bank S."""
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
TEST = ROOT/"project/experiments/block_local_native"
sys.path.insert(0, str(TEST))
from check_e_s32 import vectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=25001)
    args = parser.parse_args()
    check_native()
    cpus = len(os.sched_getaffinity(0))
    assert cpus in {10, 12}
    folder, original, flow, results = source(args.source)
    assert flow["top"] == "e_s32_ap64"
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
        netlist, proof = export(ROOT, args.out, run, folder, original, results, "e_s32_ap64", LIB)
        (args.out/"cells.ys").write_text(f"read_liberty -ignore_miss_func -ignore_miss_dir {LIB}\nwrite_verilog -noattr cells.v\n")
        run(["yosys", "-s", args.out/"cells.ys"], "cells.log")
        vectors(args.seed, args.out/"vectors.hex")
        bank = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v")
        bank_sha = "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7"
        assert sha(bank) == bank_sha
        local_bank = args.out/bank.name
        local_bank.write_bytes(bank.read_bytes())
        vlt = "/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator"
        assert "VERILATOR_ROOT" not in os.environ
        # Warnings in generated Liberty cell models do not disable assertions.
        # The exact gate netlist is the only definition of the active AP64 leaf.
        run([vlt, "--binary", "--timing", "--assert", "--timescale-override", "1ns/1ps", "-Wno-fatal",
             "--x-initial", "unique", "--x-assign", "unique", "--top-module", "test_e_s128_joint",
             "-GAP64=1'b1", "-j", cpus, "--Mdir", args.out/"obj",
             TEST/"real_s_lint.vlt", TEST/"test_e_s128_joint.sv", netlist, args.out/"cells.v",
             ROOT/"project/rtl/w8a16_v1/e_s128_frontend.sv",
             ROOT/"project/experiments/shared_x_control/rtl/native_s128_mux2.sv",
             ROOT/"project/rtl/s_sram/local_s_base.sv", ROOT/"project/rtl/s_sram/block_feed_s16k_sram.sv",
             local_bank], "build.log")
        runs = []
        for mode in range(2):
            for initial in range(3):
                log = f"mode{mode}-{initial}-{args.seed}.log"
                run([args.out/"obj/Vtest_e_s128_joint", "+vectors="+str(args.out/"vectors.hex"), f"+mode={mode}",
                     f"+verilator+rand+reset+{initial}", f"+verilator+seed+{args.seed}"], log)
                lines = (args.out/log).read_text().splitlines()
                assert sum(t.startswith("PASS e_s128_joint ") for t in lines) == 1
                assert sum(t.startswith("E_REAL_S ") for t in lines) == 100
                assert not any("%Error" in t for t in lines)
                runs.append(dict(mode=mode, initial=initial, seed=args.seed, log=log, sha256=sha(args.out/log)))
        report = dict(passed=True, source_receipt_sha256=sha(folder/"receipt.json"), full_final_netlist=proof,
            final_odb_sha256=sha(results/"6_final.odb"), runs=runs, bank_sha256=bank_sha,
            oracle_sha256=sha(args.out/"vectors.hex"),
            scope="Actual final-ODB AP64 logic with original protection loads and real four-bank private S. Two pressure modes, three initial states, exact pointwise oracle; not standalone legacy E or system STA.")
        (args.out/"final-function.json").write_text(json.dumps(report, indent=2)+"\n")
        receipt["passed"] = True
    finally:
        receipt["end_unix"] = time.time()
        receipt["outputs"] = {p.relative_to(args.out).as_posix(): sha(p) for p in args.out.rglob("*") if p.is_file()}
        (args.out/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    main()
