"""Prove cycle-equivalence of two mapped netlists using matched flop cuts."""

import json
import re
import subprocess


def yosys_run(yosys, script, directory, log):
    result = subprocess.run([yosys, "-Q", "-p", script], cwd=directory, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    (directory / log).write_bytes(result.stdout)
    return result.returncode, result.stdout.decode(errors="replace")


def cut(module):
    flops = {}
    bit_numbers = [b for item in module["netnames"].values() for b in item["bits"] if isinstance(b, int)]
    next_bit = max(bit_numbers) + 1
    for index, (name, cell) in enumerate(sorted(module["cells"].items())):
        kind = cell["type"]
        if not re.fullmatch(r"(?:S?DFF[A-Z]*)_X\d+", kind):
            continue
        links = cell["connections"]
        inputs = sorted(pin for pin, direction in cell["port_directions"].items() if direction == "input")
        outputs = set(pin for pin, direction in cell["port_directions"].items() if direction == "output")
        if not outputs or outputs - {"Q", "QN"} or any(len(links[p]) != 1 for p in inputs):
            raise ValueError(f"unexpected flop pin contract: {name} {kind}")
        flops[name] = (kind.rsplit("_X", 1)[0], tuple(inputs))
        # Derive port names from the flop identity, independent of combinational cell insertions.
        stem = "timing_cut" + name
        q = links.get("Q") or [next_bit]
        next_bit += 1
        if len(q) != 1 or not isinstance(q[0], int):
            raise ValueError(f"invalid Q for {name}")
        module["ports"][stem] = dict(direction="input", bits=q)
        module["netnames"][stem] = dict(hide_name=0, bits=q, attributes={})
        del module["cells"][name]
        if links.get("QN"):
            module["cells"][f"timing_invert_{index}"] = dict(
                hide_name=0, type="$not", parameters=dict(A_SIGNED="0", A_WIDTH="1", Y_WIDTH="1"),
                attributes={}, port_directions=dict(A="input", Y="output"), connections=dict(A=q, Y=links["QN"]))
        for pin in inputs:
            port = stem + "_" + pin
            module["ports"][port] = dict(direction="output", bits=links[pin])
            module["netnames"][port] = dict(hide_name=0, bits=links[pin], attributes={})
    if not flops:
        raise ValueError("no flop cutpoints")
    return flops


def prove(yosys, liberty, top, directory):
    extracted = {}
    for tag, source in (("gold", "mapped.v"), ("repaired", "repaired.v")):
        status, log = yosys_run(
            yosys, f'read_liberty -lib -ignore_miss_func "{liberty}"; read_verilog {source}; '
            f'hierarchy -check -top {top}; write_json {tag}.json', directory, f"{tag}-read.log")
        if status:
            return dict(passed=False, stage=tag + " parse", exit_code=status, detail=log[-1000:])
        module = json.loads((directory / f"{tag}.json").read_bytes())["modules"][top]
        ports = {p: (v["direction"], len(v["bits"])) for p, v in module["ports"].items()}
        flops = cut(module)
        extracted[tag] = (ports, flops)
        module["attributes"] = {}
        (directory / f"{tag}-cut.json").write_text(json.dumps({"modules": {tag: module}}), encoding="utf-8")
    if extracted["gold"] != extracted["repaired"]:
        return dict(passed=False, stage="register or port correspondence")
    code, log = yosys_run(
        yosys, f'read_liberty -ignore_miss_func "{liberty}"; read_json gold-cut.json; '
        'read_json repaired-cut.json; miter -equiv -flatten gold repaired timing_proof; '
        'hierarchy -top timing_proof; opt -full; check -assert; sat -verify -timeout 180 -prove trigger 0',
        directory, "equivalence.log")
    passed = code == 0 and "SAT proof finished - no model found: SUCCESS!" in log
    print(f"{directory.name}: equivalence {'PASS' if passed else 'FAIL'}", flush=True)
    return dict(passed=passed, compared_registers=len(extracted["gold"][1]),
                compared_public_ports=len(extracted["gold"][0]), exit_code=code,
                detail=None if passed else log[-1800:])
