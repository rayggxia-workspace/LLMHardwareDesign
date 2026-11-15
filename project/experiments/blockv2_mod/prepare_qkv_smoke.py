"""Prepare the first-layer QKV smoke case from archived machine evidence."""
import json
from pathlib import Path
import sys

page, out = map(Path, sys.argv[1:])
prior = json.loads((page / "algo1-result.json").read_text())
hardware = prior["resolved_hardware"]
hardware["control_groups"]["P0"] = hardware["control_groups"].pop("projection")
spec = hardware["event_model"]
for record in (*spec["routes"].values(), *spec["services"].values()):
    record["native_providers"]["P0"] = record["native_providers"].pop("projection")
calls = json.loads((page / "deployment.json").read_text())["calls"]
contracts = {}
for record in (*spec["routes"].values(), *spec["services"].values()):
    provider = record["native_providers"]["P0"]
    prefix = {"bias": "ADD", "load": "DRL", "store": "KVR"}.get(provider)
    if provider.startswith("rope-"):
        prefix = "RPE"
    by_key = {}
    for call in calls:
        schema, abi, opcode = call["service_signature"]
        kind = {3: "ADD", 0x02505001: "P", 0x314c5244: "DRL",
                0x31455052: "RPE", 0x3152564b: "KVR"}[schema]
        if (prefix and prefix == kind) or (prefix is None and provider == call["binding_id"] and kind == "P"):
            by_key[schema, abi, opcode] = dict(schema=schema, abi=abi, opcode=opcode,
                                              completion=call["required_completion"])
    if not by_key:
        raise ValueError(f"no machine evidence for {provider}")
    contracts[provider] = {"calls": list(by_key.values())}
hardware["native_provider_contracts"] = contracts
out.mkdir(parents=True, exist_ok=True)
(out / "qkv-event-ir.json").write_text(json.dumps(prior["event_ir"]))
(out / "qkv-hardware.json").write_text(json.dumps(hardware))
