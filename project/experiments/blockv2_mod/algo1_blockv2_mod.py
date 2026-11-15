"""Historical symbolic diagnostic; not the current macro-native compiler."""
import argparse
from hashlib import sha256
import json
from pathlib import Path



def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_ir", type=Path)
    parser.add_argument("hardware", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--legacy-symbolic-diagnostic", action="store_true",
                        help="explicitly run the retired symbolic prototype; emits no machine code")
    args = parser.parse_args()
    if not args.legacy_symbolic_diagnostic:
        parser.error("retired symbolic entry: use the current macro-native flow in README.md; "
                     "this diagnostic does not emit hardware instructions")
    from event_native_dispatch import qualify_native_dispatch
    from dispatch_responsibility import responsibilities
    from run import compile_event_ir

    root = Path(__file__).resolve().parent
    profile_path = root / "algo1/blockv2-mod.json"
    profile = read(profile_path)
    rtl_sources = profile["rtl_sources_sha256"]
    if not rtl_sources:
        raise ValueError("Block V2 RTL profile requires source fingerprints")
    for name, expected in rtl_sources.items():
        source = (root / "rtl" / name).resolve()
        if not source.is_relative_to(root / "rtl") or sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Block V2 RTL profile is stale: {name}")
    hardware = qualify_native_dispatch(read(args.hardware), rtl_profile=profile)
    result = compile_event_ir(read(args.event_ir), hardware, emit_outputs=True)
    spec = hardware["event_model"]
    result["implementation_gaps"] = responsibilities(hardware)
    if result["status"] != "planned" and result["implementation_gaps"]:
        result["failure_stage"] = "native_candidate_admission"
    result["delivery_accepted"] = False
    result["artifact_scope"] = "whole-graph symbolic planning and native admission; machine-code emission is not implemented in this entry"
    result["hardware_scope"] = "blockv2-mod RTL interfaces"
    result["rtl_profile_sha256"] = sha256(profile_path.read_bytes()).hexdigest()
    result["rtl_sources_sha256"] = rtl_sources
    result["rtl_interface_requirements"] = {
        section: {name: record["rtl_interface_requirements"]
                  for name, record in spec[section].items()
                  if "rtl_interface_requirements" in record}
        for section in ("routes", "services")
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
