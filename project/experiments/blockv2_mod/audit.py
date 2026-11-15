import json
from pathlib import Path
import sys

preflight, base, output = map(Path, sys.argv[1:])
audit = json.loads(preflight.read_text())
base_data = json.loads(base.read_text())
targets = {target["id"]: target for target in base_data["native_service_routes"]["targets"]}
names = {
    (0, 3, 2): "P0 ADD",
    (3, 3, 2): "U0 ADD",
    (3, 3, 3): "U0 RMSNorm",
    (0, 0x02505001, 2): "P0 projection",
}
qkv = json.loads((output.parent / "qkv-terminal-audit.json").read_text())
assert qkv["calls"] == 84
rows = []
for service in audit["services"]:
    if service["status"] == "missing_tlm_model":
        continue
    signature = service["signature"]
    target = targets[signature["target"]]
    schema, abi, opcode = (signature[k] for k in ("schema", "abi", "opcode"))
    completion = signature["completion"]
    available = [
        route["completions"] for route in target["routes"]
        if (route["schema"], route["abi"], route["opcode"]) == (schema, abi, opcode)
    ]
    name = names.get((target["id"], schema, opcode))
    if name is None:
        name = (schema.to_bytes(4, "little").decode() if schema >= 1 << 24 else "P0 projection")
        if name == "KVR1":
            name += f"/{opcode}"
    expected = "missing_completion_provider" if available else "missing_native_dispatch"
    assert not any(completion in items for items in available)
    assert expected == service["status"], (signature, available)
    rows.append({
        "operation": name, "group": target["group"], "signature": signature,
        "required_completion": completion, "base_completions": available,
        "status": expected, "sample": service["sample"],
        "fixture_111756": name in {"P0 ADD", "DRL1", "RPE1", "KVR1/1", "KVR1/2"}
        or completion == "service_done" and name == "P0 projection",
    })
assert len(rows) == 14
assert sum(row["status"] == "missing_native_dispatch" for row in rows) == 12
output.write_text(json.dumps(rows, indent=2) + "\n")
for row in rows:
    print(row["group"], row["operation"], row["required_completion"], row["status"],
          "component-pass" if row["fixture_111756"] else "")
