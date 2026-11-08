"""Compare the protected synthesis seed and ODB netlist across every SRAM pin."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess

from physical import BANK, BANK_HASHES, STDLIB, sha
from native_formal import inspect
from native_logic_projection import project
from structural_view import compare


def cut(data, top):
    module = data["modules"][top]
    banks = sorted(name for name, cell in module["cells"].items() if cell["type"] == BANK)
    assert len(banks) == 4
    contract = {"clk0": ("input", 1), "csb0": ("input", 1), "web0": ("input", 1),
                "addr0": ("input", 8), "din0": ("input", 128), "dout0": ("output", 128)}
    for index, name in enumerate(banks):
        cell = module["cells"].pop(name)
        assert not cell["parameters"] and set(cell["connections"]) == set(contract)
        for pin, (direction, width) in contract.items():
            bits = cell["connections"][pin]
            assert len(bits) == width and cell["port_directions"][pin] == direction
            port = f"__sram_{index}_{pin}"
            assert port not in module["ports"] and port not in module["netnames"]
            module["ports"][port] = dict(direction="output" if direction == "input" else "input", bits=bits[:])
            module["netnames"][port] = dict(hide_name=0, bits=bits[:], attributes={})
    return banks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--netlist", type=Path, required=True)
    parser.add_argument("--bank-lib", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("SLURM_JOB_ID") and sha(args.bank_lib) == BANK_HASHES["lib"]
    candidate = args.candidate.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True)
    top = json.loads((candidate / "receipt.json").read_text())["top"]
    gold = candidate / "input.v"
    seeded = candidate / f"flow/results/nangate45/{top}/base/1_2_yosys.v"
    assert sha(gold) == sha(seeded) and not seeded.stat().st_mode & 0o222

    def run(command, name, check=True):
        with (out / f"{name}.log").open("w") as log:
            return subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT, check=check)

    def yosys(name, text):
        script = out / f"{name}.ys"
        script.write_text(text)
        run(["yosys", "-s", script], name)

    libs = f"read_liberty -lib {STDLIB}\nread_liberty -lib {args.bank_lib}\n"
    graphs, identities = {}, {}
    for label, netlist in (("gold", gold), ("gate", args.netlist)):
        yosys(f"{label}-parse", libs + f"read_verilog {netlist}\nhierarchy -check -top {top}\n"
                                     f"write_json {label}-physical.json\n")
        data = json.loads((out / f"{label}-physical.json").read_text())
        data, projection = project(data, STDLIB.read_text())
        assert bool(projection["removed_count"]) == (label == "gate")
        identities[label] = cut(data, top)
        graphs[label] = data
    assert identities["gold"] == identities["gate"]

    negative = copy.deepcopy(graphs["gate"])
    module = negative["modules"][top]
    port = "__sram_0_addr0"
    old = module["ports"][port]["bits"][0]
    bit = max(b for net in module["netnames"].values() for b in net["bits"] if isinstance(b, int)) + 1
    module["cells"]["__negative_address_inverter"] = dict(
        type="INV_X1", parameters={}, attributes={}, port_directions={"A": "input", "ZN": "output"},
        connections={"A": [old], "ZN": [bit]})
    module["ports"][port]["bits"][0] = bit
    module["netnames"][port]["bits"][0] = bit
    graphs["negative"] = negative
    for label, graph in graphs.items():
        (out / f"{label}-cut.json").write_text(json.dumps(graph))
        yosys(f"{label}-emit", f"read_json {label}-cut.json\n"
                              f"write_verilog -noattr -noexpr -norename {label}-cut.v\ndesign -reset\n"
                              f"read_liberty -lib {STDLIB}\nread_verilog {label}-cut.v\n"
                              f"hierarchy -check -top {top}\nwrite_json {label}-readback.json\n")
        compare(graph, json.loads((out / f"{label}-readback.json").read_text()))

    proof = {}
    for label in ("gate", "negative"):
        log = out / f"{label}-kepler.log"
        config = out / f"{label}.yml"
        config.write_text(f"format: verilog\ninput_paths:\n  - {out}/gold-cut.v\n  - {out}/{label}-cut.v\n"
                          f"liberty_files:\n  - {STDLIB}\nlog_file: {log}\n")
        tool = "/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal"
        rc = run([tool, "--config", config], f"{label}-command", check=False).returncode
        text = log.read_text()
        proof[label] = inspect(text)
        proof[label]["returncode"] = rc
        if label == "gate":
            assert rc == 0 and proof[label]["passed"]
        else:
            assert not proof[label]["passed"] and (
                "Found difference" in text or re.search(r"SAT solver finished: SAT\s*$", text, re.M))
    (out / "formal.json").write_text(json.dumps(dict(
        top=top, passed=True, banks=identities["gate"], proof=proof,
        seed_sha256=sha(gold), odb_export_sha256=sha(args.netlist)), indent=2) + "\n")


if __name__ == "__main__":
    main()
