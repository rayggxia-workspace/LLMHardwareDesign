"""Lower the complete ONNX graph using its bound integer program."""
import argparse
import json
from pathlib import Path

from event_loop_graph import lower
from frontend import import_onnx
from leaf_catalog import read_profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("model", "hardware", "integer_program", "qualification", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    graph = import_onnx(args.model)
    hardware = json.loads(args.hardware.read_text())
    program = json.loads(args.integer_program.read_text())
    profile = read_profiles([(args.qualification / f"native-{n}.log").read_text()
                             for n in range(3)])
    rtl_inventory = json.loads((Path(__file__).parent / "algo1/blockv2-mod.json").read_text())
    inventory = hardware["leaf_inventory"]
    hardware["topology_id"] = rtl_inventory["topology_id"]
    hardware["control_groups"] = {name: {"site": entry["site"]}
                                  for name, entry in inventory.items()}
    # The route registry is a partial overlay, not a complete block inventory.
    declared = {target["group"]: target["id"] for target in rtl_inventory["targets"]}
    unknown = sorted(set(declared) - set(inventory))
    if unknown:
        raise ValueError("dispatch overlay names absent resource instances: " + str(unknown))
    for group, block_id in declared.items():
        hardware["control_groups"][group]["block_id"] = block_id
    event_ir, resolved, audit = lower(graph, hardware, program, profile)
    if not audit["passed"]:
        raise ValueError("full-graph lowering failed verification")
    args.output.mkdir()
    for file, data in (("event-ir.json", event_ir), ("hardware.json", resolved),
                       ("lowering-audit.json", audit)):
        (args.output / file).write_text(json.dumps(data, separators=(",", ":")) + "\n")
    print(f"Full graph lowered: {len(event_ir['tasks'])} tasks; source {graph['sha256']}", flush=True)


if __name__ == "__main__":
    main()
