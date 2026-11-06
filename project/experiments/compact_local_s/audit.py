"""Read back routed SRAM using the original 300 MHz boundary."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from physical import BANK_HASHES, COMMON, STDLIB, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bank-lib", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("SLURM_JOB_ID") and sha(args.bank_lib) == BANK_HASHES["lib"]
    work = args.candidate.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True)
    source = json.loads((work / "receipt.json").read_text())
    top = source["top"]
    results = work / f"flow/results/nangate45/{top}/base"
    files = {kind: results / f"6_final.{kind}" for kind in ("odb", "spef", "def", "sdc", "v", "gds")}
    digests = {path.name: sha(path) for path in files.values()}

    def run(name, body):
        script = out / f"{name}.tcl"
        script.write_text(body)
        with (out / f"{name}.log").open("w") as log:
            subprocess.run(["openroad", "-no_init", "-exit", script], cwd=out,
                           stdout=log, stderr=subprocess.STDOUT, check=True)

    header = f"read_liberty {{{STDLIB}}}\nread_liberty {{{args.bank_lib}}}\n"
    inputs = f"""set ::env(BV1_ODB) {{{files['odb']}}}
set ::env(BV1_SDC) {{{work / 'input.sdc'}}}
set ::env(BV1_SPEF) {{{files['spef']}}}
"""
    sta = (COMMON / "native_sta.tcl").read_text().replace(
        "source [file join [file dirname [info script]] native_annotation.tcl]",
        f"source {{{COMMON / 'native_annotation.tcl'}}}")
    run("sta", header + inputs + sta)
    run("physical", header + inputs + (COMMON / "native_physical.tcl").read_text())
    run("native-drc", f"read_db {{{files['odb']}}}\n"
                      "drt::check_drc_cmd native-drc.rpt 0 0 0 0 native_whole_drc\n")
    run("views", header + f"read_db {{{files['odb']}}}\nread_sdc {{{work / 'input.sdc'}}}\n"
        f"read_spef {{{files['spef']}}}\nset_propagated_clock [all_clocks]\n"
        f"write_timing_model -library_name {top}_tt -cell_name {top} {top}.lib\n"
        f"write_abstract_lef -bloat_occupied_layers {top}.lef\n")
    assert digests == {path.name: sha(path) for path in files.values()}

    def read_table(name):
        return {fields[0]: fields[1:] for fields in
                (row.split("\t") for row in (out / name).read_text().splitlines())}

    timing = read_table("timing-summary.tsv")
    physical = read_table("physical-summary.tsv")
    slack = re.findall(r"(?m)^worst slack(?:\s+(?:max|min))?[ \t]+([-+.0-9]+)",
                       (out / "timing.rpt").read_text())
    assert len(slack) == 2
    from native_annotation import inspect
    from native_passive_endpoint import audit
    passive = {pin: dict(master=master, type=kind, direction=direction, net=net, pin=pin.rsplit("/", 1)[1])
               for pin, master, kind, direction, net in
               (line.split("\t") for line in (out / "passive-inventory.tsv").read_text().splitlines())}
    coverage = audit(out, out / "timed-endpoints", STDLIB.read_text(), passive)
    annotation = inspect(out)
    checks = {
        "setup_hold": min(map(float, slack)) >= 0 and all(timing[key] == ["0"]
                                                         for key in ("setup_checks", "hold_checks")),
        "electrical": all(timing[key][0] == "0" for key in ("capacitance", "slew", "fanout")),
        "timing_coverage": coverage["passed"],
        "parasitic_annotation": annotation["passed"],
        "pg_signal_placement": all(physical[k] == [v] for k, v in
            {"unplaced": "0", "open_signal_inputs": "0", "incorrect_pg_iterms": "0",
             "pg_VDD": "1", "pg_VSS": "1"}.items()),
        "native_openroad_drc": not (out / "native-drc.rpt").read_text().strip(),
        "native_gds_drc": source.get("native_gds_drc_items") == 0,
        "final_pin_rectangles": json.loads((work / "6_final-pin-proof.json").read_text())["passed"],
    }
    report = dict(top=top, final_sha256=digests, sdc_sha256=sha(work / "input.sdc"),
                  setup_ns=float(slack[0]), hold_ns=float(slack[1]), timing_summary=timing,
                  checks=checks, passed=all(checks.values()),
                  views_sha256={p.name: sha(p) for p in (out / f"{top}.lef", out / f"{top}.lib")},
                  scope="Independent native routed audit. Abstract views are candidates. "
                        "Final gate function, bank-boundary formal and upper-layer product STA are separate.")
    (out / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
