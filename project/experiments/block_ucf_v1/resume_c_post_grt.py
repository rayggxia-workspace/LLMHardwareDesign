"""Apply evidence-bound C16 ECO after deterministic global-route replay."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

source, audit, loads = (Path(arg).resolve() for arg in sys.argv[1:4])
variant, threads = map(int, sys.argv[4:])
assert variant in (1, 2) and threads == 12
root = Path.cwd()
script = Path(__file__).resolve().parent
before = source / "completion.json"
producer = json.loads(before.read_text())
audit_receipt = audit / "receipt.json"
check = json.loads(audit_receipt.read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


assert producer["policy"] in ("c-skew2", "c-skew3")
assert check["scope"] == "diagnostic timing-only" and check["input_receipt_sha256"] == sha(before)
assert check["checks"]["physical"]["passed"]
native = check["checks"]["timing"]["timing"]["timed_endpoints"]
assert native["minimum_setup_ns"] > 0 and native["minimum_hold_ns"] < 0
assert native["electrical"]["capacitance"]["slack"] < 0
assert all(sha(path) == digest for path, digest in producer["outputs"].items())
original, = {Path(path).parent for path in producer["outputs"]}
assert original.parent.name == "block_c16" and original.name == "base"
stage = root / "flow/results/nangate45/block_c16/base"
stage.mkdir(parents=True)

inputs = json.loads((source / "inputs.json").read_text())
copied = {}
for path in [source / name for name in ("mapped.v", "pins.json", "pins.tcl")] + sorted(original.iterdir()):
    if path.parent == original and not re.match(r"^[1-4]_", path.name):
        continue
    assert path.is_file()
    dest = (stage if path.parent == original else root) / path.name
    shutil.copyfile(path, dest)
    assert sha(dest) == sha(path)
    copied[str(dest)] = sha(dest)
    inputs[str(dest)] = copied[str(dest)]
assert sha(root / "mapped.v") == sha(stage / "1_2_yosys.v")
assert (stage / "4_cts.odb").is_file() and (stage / "4_cts.sdc").is_file()

hold = []
endpoints = audit / "timed-endpoints/endpoints.tsv"
for line in endpoints.read_text().splitlines():
    endpoint, _, slack, *_ = line.split("\t")
    if float(slack) < 0:
        instance, pin = endpoint.rsplit("/", 1)
        assert pin == "D" or re.fullmatch(r"(?:din0|addr0)\[\d+\]|csb0|web0", pin), endpoint
        # The F16 controlled experiment measured ~25 ps of incremental routed
        # hold gain per BUF_X1. Add one guard stage, and compare a second lane.
        stages = 1 + variant + int((-float(slack)) / 0.025)
        hold.append((instance, pin, stages))
assert 0 < len(hold) == native["native_summary"]["hold_checks"] <= 16

report = loads / "electrical-worst.rpt"
assert sha(audit / "sta.tcl") == (loads / "input.sha256").read_text().split()[0]
assert sha(report) == (loads / "result.sha256").read_text().split()[0]
cap = []
for line in report.read_text().split("max capacitance\n", 1)[1].splitlines():
    if not line.endswith(("(VIOLATED)", "(MET)")):
        continue
    endpoint, limit, load, slack, status = line.split()
    if status == "(VIOLATED)":
        assert float(load) > float(limit) > 0 and float(slack) < 0
        cap.append(endpoint.rsplit("/", 1))
    elif variant == 2 and re.search(r"\.memory/dout0\[\d+\]$", endpoint) and float(slack) < 0.12:
        cap.append(endpoint.rsplit("/", 1))
assert 0 < len(cap) < 16
for target in (*hold, *cap):
    assert not any(re.search(r"[{}\n\r]", str(value)) for value in target)

def tcl_list(rows):
    return " ".join("{" + " ".join("{" + str(value) + "}" for value in row) + "}" for row in rows)


hook_body = script / "c-post-grt.tcl"
hook = root / "post-grt-eco.tcl"
hook.write_text(f"set ucf_eco_hold {{{tcl_list(hold)}}}\nset ucf_eco_cap {{{tcl_list(cap)}}}\n"
                f"set ucf_eco_variant {variant}\nsource {{{hook_body}}}\n")
config = (source / "config.mk").read_text()
assert "POST_GLOBAL_ROUTE_TCL" not in config
(root / "config.mk").write_text(config + f"\nexport POST_GLOBAL_ROUTE_TCL = {hook}\n")
for path in (before, audit_receipt, endpoints, report, hook_body, hook, root / "config.mk"):
    inputs[str(path)] = sha(path)
(root / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
command = ["make", "-C", "/OpenROAD-flow-scripts/flow", f"DESIGN_CONFIG={root/'config.mk'}",
           f"WORK_HOME={root/'flow'}", f"NUM_CORES={threads}"]
for step in ("do-route", "do-finish", "do-gds"):
    with (root / (step + ".log")).open("w") as log:
        subprocess.run(command + [step], stdout=log, stderr=subprocess.STDOUT, check=True)
    assert all(sha(path) == digest for path, digest in copied.items())
outputs = [stage / f"6_final.{ext}" for ext in ("v", "sdc", "def", "odb", "spef", "gds")]
(root / "completion.json").write_text(json.dumps({
    "qualification": "pending", "policy": f"post-grt-{variant}", "parent_receipt": str(before),
    "diagnostic_receipt": str(audit_receipt), "resumed_checkpoint_sha256": copied,
    "outputs": {str(path): sha(path) for path in outputs}}, indent=2) + "\n")
