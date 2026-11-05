"""Verify the A1 review snapshot and report the unresolved production gates."""

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCTION_GATES = {
    "integrated_top", "fixed_control", "private_s", "intra_block_data",
    "cross_block_data", "cross_block_ack", "images_and_data",
}
TRIAL_SOURCES = {
    "project/control_p_compute_v0_1/lc_m_dot_store_adapter.sv",
    "project/control_p_compute_v0_1/tb_p_compute.sv",
    "project/control_rtl_min_v0_1/lc_min_controller.sv",
    "project/control_rtl_min_v0_1/mc_min_controller.sv",
    "project/control_rtl_min_v0_1/m_dot_store_desc.svh",
    "project/rtl/block_feed_v1/block_feed_loader.sv",
    "project/rtl/block_feed_v1/block_feed_s16k.sv",
    "project/rtl/block_local_s/block_local_s_arbiter.sv",
    "project/rtl/block_local_s/block_local_s_macro.sv",
    "project/rtl/block_v2/block_v2_m.sv",
    "project/rtl/block_v2/block_v2_g.sv",
    "project/rtl/block_v2/block_v2_g_tables.svh",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(manifest):
    require(manifest["schema"] == "a1-p-deployment-review/0.1", "unsupported review schema")
    trial = manifest["a2g"]
    evidence_bytes = (ROOT / trial["evidence"]).read_bytes()
    require(sha256(evidence_bytes).hexdigest() == trial["evidence_sha256"], "A2-G evidence changed")
    evidence = json.loads(evidence_bytes)
    require(
        (manifest["issue"], manifest["pr"], manifest["source_heads"]["PR176"]) ==
        (evidence["issue"], evidence["pr"], evidence["pr176"]),
        "A2-G lineage mismatch",
    )
    require(
        (trial["job"], trial["server_commit"], evidence["state"], evidence["exit_code"]) ==
        (evidence["job_id"], evidence["source_commit"], "COMPLETED", "0:0"),
        "A2-G job mismatch",
    )
    sources = evidence["source_manifest"]["sources"]
    require(set(trial["git_blobs"]) == TRIAL_SOURCES, "incomplete A2-G source inventory")
    for rel, blob in trial["git_blobs"].items():
        data = (ROOT / rel).read_bytes()
        require(sha256(data).hexdigest() == sources[rel], f"server source mismatch: {rel}")
        require(sha1(f"blob {len(data)}\0".encode() + data).hexdigest() == blob, f"Git blob mismatch: {rel}")

    profile = trial["private_s"]
    require(
        (trial["instances"], trial["block_id"], int(trial["resource_mask"], 16)) ==
        ({"M": 1, "G": 1, "S": 1}, 0, 0x29),
        "A2-G instance inventory mismatch",
    )
    require(
        profile["bytes"] == 16384 == (1 << profile["address_bits"]) * (profile["word_bits"] // 8),
        "16 KiB A2-G address contract mismatch",
    )
    require(
        (profile["banks"], profile["clients"], profile["write_client"], profile["host_test_client"]) == (4, 4, 0, 3),
        "A2-G S client ownership mismatch",
    )
    edges = trial["data_edges"]
    require(
        [(edge["id"], edge["bits"]) for edge in edges] == [
            ("feeder_to_m_a", 128), ("feeder_to_m_b", 512), ("m_to_adapter", 128),
            ("adapter_to_g", 32), ("g_to_adapter", 32), ("adapter_to_s", 128), ("s_to_adapter_ack", 128),
        ] and len({edge["sink"] for edge in edges}) == len(edges),
        "A2-G edge width or writer mismatch",
    )
    require(
        float(trial["clock"]["period_ns"]) == round(evidence["timing"]["period_ns"], 9),
        "A2-G clock period mismatch",
    )
    desc = ROOT / "project/control_rtl_min_v0_1/m_dot_store_desc.svh"
    words = desc.read_text(encoding="utf-8")
    for key, constant, bits in (
        ("native_abi_id", "ABI", 32), ("topology_id", "TOPOLOGY", 32), ("native_op", "OP", 16),
    ):
        value = int(trial[key], 16)
        require(f"M_SILU_STORE_{constant} = {bits}'h{value:0{bits // 4}x};" in words, f"trial {key} mismatch")

    completion = trial["completion"]
    require(
        completion == ["g_request_cycle", "g_response_cycle", "write_cycle", "ack_cycle",
                       "return_cycle", "terminal_cycle", "result_cycle"],
        "S write completion must precede service and task success",
    )
    cases = evidence["verification"]["G_cases"]
    successes = 0
    for case in cases:
        for job in case["jobs"]:
            if job["status"] != 0:
                require(job["write_bytes"] == 0, f"unexpected failed write: {case['name']}")
                continue
            cycles = [job[edge] for edge in completion]
            require(
                job["write_bytes"] == 16 and all(left < right for left, right in zip(cycles, cycles[1:])),
                f"A2-G write/ACK order mismatch: {case['name']}",
            )
            successes += 1
    require(successes == evidence["verification"]["successful_writes"] == 5, "A2-G successful write count mismatch")

    gates = manifest["production"]
    require(set(gates) == PRODUCTION_GATES, "required production gates are missing or unknown")
    # This schema records unresolved evidence. Filling in a candidate path does
    # not qualify it. A subsequent review must verify actual production bindings.
    require(all(gate["binding"] is None and gate["required"] for gate in gates.values()),
            "production binding supplied without a production review")
    return {
        "trial_source_blobs_verified": len(trial["git_blobs"]),
        "trial_write_ack_sequences_verified": successes,
        "production_ready": False,
        "pending_production": list(gates),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "deployment_a1.json")
    parser.add_argument("--require-production", action="store_true", help="exit 2 when the review is not production-ready")
    args = parser.parse_args()
    try:
        result = check(json.loads(args.manifest.read_bytes()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"A1 review invalid: {exc}\n")
    print(json.dumps(result, indent=2))
    return 2 if args.require_production and not result["production_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
