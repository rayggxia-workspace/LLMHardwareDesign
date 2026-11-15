import json
from pathlib import Path
from hashlib import sha256
import sys

from event_native_dispatch import qualify_native_dispatch
from run import compile_event_ir

page, base_path, out = map(Path, sys.argv[1:])
prior = json.loads((page / "algo1-result.json").read_text())
baseline = compile_event_ir(prior["event_ir"], prior["resolved_hardware"], emit_outputs=False)
if baseline["status"] != "planned":
    raise ValueError("archived first-layer QKV input did not plan")
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
base = json.loads(base_path.read_text())
qualified = qualify_native_dispatch(hardware, base)
result = compile_event_ir(prior["event_ir"], qualified, emit_outputs=False)
if result["status"] == "planned":
    raise ValueError("Block V2 compiled without complete native bindings")
# Observe the completed projection path in isolation. Retain every other
# unbound command and keep this RTL-only input separate from the placed base.
p0 = next(target for target in base["native_service_routes"]["targets"] if target["id"] == 0)
projection, = [route for route in p0["routes"] if route["schema"] == 0x02505001]
assert "scope_committed" in projection["completions"]
projection["completions"].append("service_done")
qualified_mod = qualify_native_dispatch(hardware, base)
result_mod = compile_event_ir(prior["event_ir"], qualified_mod, emit_outputs=False)
issues_mod = qualified_mod["event_model"]["native_dispatch_issues"]
assert not any("no physical completion" in issue for issue in issues_mod["services"].values())
assert result_mod["status"] != "planned"
out.write_text(json.dumps({
    "archived_qkv_search": baseline["status"],
    "archived_qkv_tasks": baseline["plan"]["covered_original_tasks"],
    "strict_block_v2_search": result["status"],
    "blockv2_mod_projection_only_search": result_mod["status"],
    "candidate_scope": "RTL-only projection completion assumption; used only for Algo1 diagnostic, not for deployment",
    "p0_rtl_sha256": sha256(Path("rtl/blockv2_mod_p0.sv").read_bytes()).hexdigest(),
    "p_lc_rtl_sha256": sha256(Path("rtl/blockv2_mod_p_native_lc.sv").read_bytes()).hexdigest(),
    "original_issues": qualified["event_model"]["native_dispatch_issues"],
    "remaining_issues": issues_mod,
}, indent=2) + "\n")
