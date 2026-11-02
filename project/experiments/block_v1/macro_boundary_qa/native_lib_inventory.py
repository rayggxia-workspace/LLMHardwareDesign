"""Independently enumerate native model pins and timing arc groups."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import time

from audit import Bundle, audit_source, file_sha, require, load_json
from native_pair import native_log_diagnostics, rows


def receive(folder, expected_ports):
    folder = Path(folder)
    ports = {}
    for name, direction, pg in rows(folder / "model-ports.tsv"):
        require(name not in ports and direction in ("input", "output", "inout", "power", "ground") and pg in ("0", "1"), "model native pin metadata")
        if direction in ("power", "ground") or pg == "1":
            require((name, direction, pg) in (("VDD", "power", "1"), ("VSS", "ground", "1")), "typed model supply role")
        ports[name] = {"direction": direction, "is_power_ground": pg == "1"}
    require({name: value["direction"] for name, value in ports.items() if name not in ("VDD", "VSS")} == expected_ports,
            "model native signal pins")
    groups, role_counts = {}, Counter()
    for row in rows(folder / "model-arc-groups.tsv"):
        require(len(row) == 7, "model arc group arity")
        index, start, end, name, is_check, condition, count = row
        require(index.isdigit() and index not in groups and (start in ports or start == "__NO_FROM_PIN__") and end in ports
                and is_check in ("0", "1") and count.isdigit() and int(count) > 0, "model arc identity")
        # Keep the full native role-bearing name; do not infer Liberty syntax
        # or replace conditional groups with an endpoint cross product.
        prefix = f"{start} -> {end} "
        require(prefix in name, "model arc scoped native name")
        role = name.split(prefix, 1)[1]
        role_counts[role] += 1
        groups[index] = {"from": start, "to": end, "native_name": name, "role": role,
                         "is_check": is_check == "1", "condition": bytes.fromhex(condition).decode(),
                         "declared_arc_count": int(count), "arcs": {}}
    require(groups and set(groups) == {str(i) for i in range(len(groups))}, "model group coverage")
    for group, index, start, end in rows(folder / "model-arcs.tsv"):
        require(group in groups and index.isdigit() and index not in groups[group]["arcs"]
                and start in ("rise", "fall", "none") and end in ("rise", "fall"), "model transition arc identity")
        groups[group]["arcs"][index] = [start, end]
    for group in groups.values():
        require(set(group["arcs"]) == {str(i) for i in range(group["declared_arc_count"])}, "model transition arc coverage")
    supply_arcs = [index for index, g in groups.items() if {g["from"], g["to"]} & {"VDD", "VSS"}]
    return {"schema": "block-v1-native-model-inventory/1", "passed": True, "ports": ports,
            "arc_groups": groups, "role_group_counts": dict(role_counts), "group_count": len(groups),
            "transition_arc_count": sum(g["declared_arc_count"] for g in groups.values()),
            "native_role_metadata_complete": all(g["from"] != "__NO_FROM_PIN__" for g in groups.values()),
            "supply_arc_groups": supply_arcs, "flat_abstract_boundary_qualified": False,
            "scope": "Native model metadata only; arc existence is not flat correspondence or numerical equivalence"}


def verify(index, folder, executable):
    bundle, folder = Bundle(index), Path(folder)
    audit_source(bundle)
    receipt = load_json((folder / "receipt.json").read_bytes())
    require(receipt["schema"] == "block-v1-native-model-inventory-receipt/1" and receipt["passed"] is True
            and receipt["returncode"] == 0, "model inventory receipt failed")
    require(receipt["inputs"]["index"] == file_sha(bundle.index_path)
            and receipt["inputs"]["model"] == bundle.digest("lib")
            and receipt["inputs"]["executable"] == file_sha(Path(executable)), "model inventory input binding")
    actual = {p.name for p in folder.iterdir() if p.is_file() and p.name != "receipt.json"}
    require(actual == receipt["outputs"].keys(), "model inventory output set")
    for name, digest in receipt["outputs"].items():
        require(Path(name).name == name and file_sha(folder / name) == digest, "model inventory output binding")
    require(file_sha(folder / "liberty_inventory.tcl") == receipt["inputs"]["collector"], "model inventory executed collector binding")
    require(receipt["command"]["environment"]["BV1QA_MODEL"] == str(bundle.paths["lib"])
            and receipt["command"]["environment"]["BV1QA_CELL"] == f"BV1_{bundle.index['top']}_{bundle.index['policy']}/{bundle.index['top']}",
            "model inventory native command scope")
    require(native_log_diagnostics(folder / "native.log")["native_error_count"] == 0, "model inventory native printed errors")
    result = receive(folder, {p["pin"]: p["direction"] for p in bundle.obj("pins")["pins"]})
    require(result == load_json((folder / "model-inventory.json").read_bytes()), "model inventory JSON disagrees with TSV")
    bundle.unchanged()
    return {"passed": True, "receipt_sha256": file_sha(folder / "receipt.json"),
            "native_role_metadata_complete": result["native_role_metadata_complete"], "qualified_hard_macro": False}


def execute(index, output, executable):
    bundle = Bundle(index)
    audit_source(bundle)
    output, executable = Path(output).resolve(), Path(executable).resolve()
    require(all(not output.is_relative_to(p.parent) for p in bundle.paths.values()), "model inventory output inside source")
    script = Path(__file__).with_name("liberty_inventory.tcl")
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "block-v1-native-model-inventory-receipt/1", "passed": False, "started": time.time(),
               "inputs": {"index": file_sha(bundle.index_path), "model": bundle.digest("lib"),
                          "executable": file_sha(executable), "collector": file_sha(script)}, "outputs": {}}
    try:
        (output / "liberty_inventory.tcl").write_bytes(script.read_bytes())
        env = dict(os.environ, OMP_NUM_THREADS="1", BV1QA_MODEL=str(bundle.paths["lib"]),
                   BV1QA_CELL=f"BV1_{bundle.index['top']}_{bundle.index['policy']}/{bundle.index['top']}")
        argv = [str(executable), "-no_init", "-exit", str(script.resolve())]
        receipt["command"] = {"argv": argv, "environment": {k: env[k] for k in ("OMP_NUM_THREADS", "BV1QA_MODEL", "BV1QA_CELL")}}
        with (output / "native.log").open("w") as stream:
            code = subprocess.run(argv, cwd=output, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
        receipt["returncode"] = code
        require(code == 0 and native_log_diagnostics(output / "native.log")["native_error_count"] == 0, "native model inventory failed")
        expected = {p["pin"]: p["direction"] for p in bundle.obj("pins")["pins"]}
        result = receive(output, expected)
        (output / "model-inventory.json").write_text(json.dumps(result, indent=2)+"\n")
        bundle.unchanged()
        require(file_sha(executable) == receipt["inputs"]["executable"]
                and file_sha(script) == receipt["inputs"]["collector"], "model inventory tool changed")
        receipt["passed"] = True
        return result
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        receipt["finished"] = time.time()
        receipt["outputs"] = {p.name: file_sha(p) for p in output.iterdir() if p.is_file() and p.name != "receipt.json"}
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index")
    parser.add_argument("output")
    parser.add_argument("--executable", required=True)
    args = parser.parse_args()
    result = execute(args.index, args.output, args.executable)
    print(json.dumps({k: result[k] for k in ("passed", "group_count", "transition_arc_count", "role_group_counts", "supply_arc_groups")}))
