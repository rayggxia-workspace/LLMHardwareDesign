"""Map and repair the six timed configurations under the fixed 300 MHz clock."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "control_r7_v0_1"))
import synthesize
from equivalence import prove, yosys_run

NAMES = ("mother", "local0", "local1", "raw16_adapter", "dma_bridge", "group_dma")


def snapshots(log):
    result = {}
    for stage, section in re.findall(r"CONTROL_TIMING (\w+)\n(.*?)(?=CONTROL_TIMING |\Z)", log, re.S):
        wns = re.search(r"(?m)^worst slack max\s+(-?[\d.]+)", section)
        hold = re.search(r"(?m)^worst slack min\s+(-?[\d.]+)", section)
        tns = re.search(r"(?m)^tns max\s+(-?[\d.]+)", section)
        paths = re.findall(r"(?ms)^Startpoint: (.*?)\nEndpoint: (.*?)\n", section)
        if not (wns and tns and hold and paths):
            raise ValueError(f"incomplete timing section {stage}")
        result[stage] = dict(wns_ns=float(wns[1]), tns_ns=float(tns[1]), hold_ns=float(hold[1]), paths=paths)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openroad", required=True)
    parser.add_argument("--yosys", required=True)
    parser.add_argument("--platform", type=Path, required=True)
    parser.add_argument("--mapped", type=Path, required=True, help="existing R7 synthesis output")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--modules", nargs="+", default=NAMES)
    args = parser.parse_args()
    mapped, out, platform = (p.resolve() for p in (args.mapped, args.out, args.platform))
    out.mkdir(parents=True, exist_ok=True)
    report = json.loads((mapped / "synthesis-report.json").read_bytes())
    src = {m["name"]: m for m in report["modules"]}
    if missing := set(args.modules) - src.keys():
        parser.error("configurations missing from mapped report: " + ", ".join(sorted(missing)))
    liberty = platform / "lib/NangateOpenCellLibrary_typical.lib"
    for filename, directory, expected in [
        ("NangateOpenCellLibrary_typical.lib", "lib", synthesize.EXPECTED_LIB_SHA),
        *((name, "lef", sha) for name, sha in synthesize.LEF_SHA.items()),
    ]:
        if synthesize.sha(platform / directory / filename) != expected:
            raise ValueError(f"unexpected {filename} digest")

    def repair(name):
        row = src[name]
        directory = out / name
        directory.mkdir()
        source = mapped / name / "mapped.v"
        if synthesize.sha(source) != row["artifacts_sha256"]["mapped.v"]:
            raise ValueError(f"{name}: netlist digest mismatch")
        shutil.copyfile(source, directory / "mapped.v")
        # OpenDB's Verilog writer needs physical drivers for constant output bits.
        tie_code, tie_log = yosys_run(
            args.yosys, f'read_liberty -lib -ignore_miss_func "{liberty}"; read_verilog mapped.v; '
            f'hierarchy -check -top {row["module"]}; '
            'hilomap -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z; check -assert; '
            'write_verilog -noattr -noexpr tied.v', directory, "ties.log")
        if tie_code:
            print(f"{name}: cannot materialize ties\n{tie_log[-1800:]}", flush=True)
            return dict(module=name, exit_code=tie_code, scope="failed tie mapping")
        env = dict(os.environ, CONTROL_N45=str(platform), CONTROL_TOP=row["module"],
                   CONTROL_CLK=row["timing"]["clock_port"])
        command = [args.openroad, "-no_init", "-exit", str(HERE / "repair.tcl")]
        run = subprocess.run(command, cwd=directory, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        log = run.stdout.decode("utf-8", errors="replace")
        (directory / "repair.log").write_bytes(run.stdout)
        if run.returncode:
            print(f"{name}: OpenROAD exit {run.returncode}\n{log[-2400:]}", flush=True)
            return dict(module=name, exit_code=run.returncode, scope="failed OpenROAD run",
                        artifacts_sha256={p.name: synthesize.sha(p) for p in directory.iterdir() if p.is_file()})
        steps = snapshots(log)
        if set(steps) != {"mapped", "placed", "buffered", "repaired", "routed_initial", "routed"}:
            raise ValueError(f"{name}: incomplete repair stages")
        area = re.findall(r"Design area\s+([\d.]+)", log)
        electrical = re.search(r"(?m)^CONTROL_ELECTRICAL final=(\d+)$", log)
        if not electrical:
            raise ValueError(f"{name}: missing final electrical report")
        result = dict(module=name, top=row["module"], clock=env["CONTROL_CLK"],
                      period_ns=10 / 3, original_mapping_ns=row["timing"]["setup_slack_ns"],
                      steps=steps, mapped_area_um2=row["cell_area_um2"],
                      repaired_area_um2=float(area[-1]) if area else None, exit_code=0,
                      electrical_violations=int(electrical[1]))
        print(f"{name}: " + ", ".join(f"{key} {value['wns_ns']:+.6f} ns" for key, value in steps.items()),
              flush=True)
        result["equivalence"] = prove(args.yosys, liberty, row["module"], directory)
        result["artifacts_sha256"] = {p.name: synthesize.sha(p) for p in directory.iterdir() if p.is_file()}
        return result

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(repair, args.modules))
    data = dict(schema="control-timing-300mhz/0.1", period_ns=10 / 3, modules=results,
                synthesis_report_sha256=synthesize.sha(mapped / "synthesis-report.json"),
                script_sha256=synthesize.sha(HERE / "repair.tcl"))
    (out / "repair-report.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if any(row["exit_code"] or row["electrical_violations"] or not row["equivalence"]["passed"] or row["steps"]["routed"]["wns_ns"] < 0
           or row["steps"]["routed"]["tns_ns"] != 0 or row["steps"]["routed"]["hold_ns"] < 0 for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
