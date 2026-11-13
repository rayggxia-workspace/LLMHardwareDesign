"""Validate the #265 freeze and verify staged inputs before Slurm submission."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


MANIFEST = Path(__file__).with_name("run-manifest.json")
PROFILES = ("legacy", "candidate_250")
CONTEXTS = (128, 128, 512, 512, 2048, 2048)
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_SHA = re.compile(r"[0-9a-f]{40}")
SSH_FINGERPRINT = re.compile(r"SHA256:[A-Za-z0-9+/]{43}")
REQUIRED_MODEL_FILES = {
    "config.json", "generation_config.json", "merges.txt", "vocab.json",
    "model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors",
    "model.safetensors.index.json", "tokenizer.json", "tokenizer_config.json",
}
REQUIRED_RUNTIME = {
    "core_clock_hz", "sram_contract", "ddr_capacity_bytes",
    "ddr_bandwidth_bytes_per_second", "ddr_configuration", "cdc_contract",
    "images", "topology", "launcher", "toolchain", "container", "build_inputs",
    "compiler_commit", "rtl_commit",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_sha(value, label):
    require(isinstance(value, str) and SHA256.fullmatch(value), f"{label}: invalid SHA-256")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(data):
    require(type(data["schema_version"]) is int and data["schema_version"] == 1,
            "unsupported manifest schema")
    require(data["issue"] == 265 and data["branch"] == "task/265-qwen3b-system-evaluation",
            "manifest belongs to another task")
    workload = data["workload"]
    for name, expected in {
        "batch": 1, "output_tokens": 128, "cached_decode_steps": 127,
        "primary_prompt_tokens": 512, "layers": 36, "vocab_size": 151936,
    }.items():
        require(type(workload[name]) is int and workload[name] == expected, f"wrong {name}")
    require(tuple(workload["case_contexts"]) == CONTEXTS, "wrong context matrix")
    require(workload["sampling"] == "greedy" and workload["stop_policy"] == "fixed_output_count",
            "wrong generation policy")
    require(workload["integer_reference_relative_l2_max"] == 0.02
            and workload["same_prefix_top1_required"] is True, "changed quality gate")
    for name, revision in {
        **data["revisions"],
        "inherited_commit": data["inherited_commit"],
        "checkpoint_revision": workload["publisher_revision"],
    }.items():
        require(isinstance(revision, str) and GIT_SHA.fullmatch(revision), f"invalid {name}")

    require(set(data["checkpoint"]) == REQUIRED_MODEL_FILES, "checkpoint file set changed")
    for name, digest in data["checkpoint"].items():
        check_sha(digest, name)
    cases = data["cases"]
    require(len(cases) == len(CONTEXTS), "wrong case count")
    for index, (case, context) in enumerate(zip(cases, CONTEXTS)):
        require(case["id"] == f"case-{index}" and case["prompt_tokens"] == context,
                f"wrong case identity at position {index}")
        require(case["prefill_onnx"] == f"export-{index // 2}/cached.onnx", "wrong prefill mapping")
        check_sha(case["tokens_sha256"], case["id"])
        check_sha(case["reference_receipt_sha256"], case["id"])
    require(len({c["tokens_sha256"] for c in cases}) == len(cases), "duplicate token artifact")

    inputs = data["historical_inputs"]
    check_sha(inputs["weights_index_sha256"], "calibration output index")
    check_sha(inputs["calibration_sha256"], "calibration")
    require(inputs["weights_count"] == 434, "wrong historical weight count")
    graph_names = {c["prefill_onnx"] for c in cases} | {"template-full/template.onnx"}
    require(set(inputs["onnx"]) == graph_names, "wrong historical graph set")
    for name, digest in inputs["onnx"].items():
        if digest is not None:
            check_sha(digest, name)
    if inputs["onnx_external_data"] is not None:
        for name, digest in inputs["onnx_external_data"].items():
            require(name not in graph_names, f"external data conflicts with ONNX: {name}")
            check_sha(digest, name)
    check_sha(data["profiles"]["legacy"]["compiler_profile"]["sha256"], "legacy resource profile")
    server = data["server"]
    fingerprint = server["host_key_fingerprint"]
    if fingerprint is not None:
        require(isinstance(fingerprint, str) and SSH_FINGERPRINT.fullmatch(fingerprint),
                "expected a verified SSH SHA256 fingerprint")
    for field in ("verified_checkpoint_path", "verified_toolchain_path"):
        value = server[field]
        if value is not None:
            require(isinstance(value, str) and value.startswith("/")
                    and ".." not in value.split("/"), f"invalid {field}")
    require(set(data["profiles"]) == set(PROFILES), "wrong profile set")
    for name in PROFILES:
        runtime = data["profiles"][name]["runtime"]
        require(REQUIRED_RUNTIME <= runtime.keys(), f"{name}: missing runtime fields")
        if name == "candidate_250":
            require("quantized_inputs" in runtime, "candidate lacks separate W8 input identity")
        for field, value in runtime.items():
            if value is None:
                continue
            if field in data["runtime_artifact_names"]:
                check_sha(value, f"{name}/{field}")
            elif field in {"compiler_commit", "rtl_commit"}:
                require(isinstance(value, str) and GIT_SHA.fullmatch(value), f"invalid {name}/{field}")
            else:
                require(type(value) is int and value > 0, f"{name}/{field}: expected positive integer")


def safe_file(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and not relative.anchor and ".." not in relative.parts,
            f"unsafe artifact path: {name}")
    path = (root / relative).resolve()
    require(root in path.parents, f"artifact escapes staged root: {name}")
    return path


def verify_file(root, name, expected):
    path = safe_file(root, name)
    require(path.is_file(), f"missing staged file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    require(digest.hexdigest() == expected, f"SHA-256 mismatch: {path}")
    return path


def verify_index(root, path, expected=None, weights_only=False):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        require(separator and name not in rows, f"invalid or duplicate checksum row in {path}")
        check_sha(digest, name)
        rows[name] = digest
    require(rows, f"empty checksum index: {path}")
    if weights_only:
        weights = {name: digest for name, digest in rows.items()
                   if name.startswith("generated/weights/") and name.endswith(".npy")}
        require(len(weights) == expected, "historical weight index has the wrong member count")
        rows = {"generated/calibration.json": rows["generated/calibration.json"], **weights}
    for name, digest in rows.items():
        verify_file(root, name, digest)
    return rows


def verify_inputs(data, root, profile):
    checkpoint = safe_file(root, "checkpoint")
    for name, digest in data["checkpoint"].items():
        verify_file(checkpoint, name, digest)
    expected_checkpoint = {name: digest for name, digest in data["checkpoint"].items()
                           if name.endswith(".safetensors") or name == "config.json"}
    vocab_size = data["workload"]["vocab_size"]
    for case in data["cases"]:
        case_root = safe_file(root, f"reference/{case['id']}")
        tokens = read_json(verify_file(case_root, "tokens.json", case["tokens_sha256"]))
        receipt = read_json(verify_file(case_root, "receipt.json", case["reference_receipt_sha256"]))
        require(receipt["checkpoint_files_sha256"] == expected_checkpoint
                and receipt["tokens_sha256"] == case["tokens_sha256"]
                and receipt["batch"] == 1 and receipt["prompt_tokens"] == case["prompt_tokens"]
                and receipt["generated_tokens"] == 128, f"{case['id']}: wrong reference receipt")
        prompt = tokens["prompt"]
        require(len(prompt) == case["prompt_tokens"]
                and all(type(token) is int and 0 <= token < vocab_size for token in prompt),
                f"{case['id']}: invalid prompt IDs")

    inputs = data["historical_inputs"]
    if profile == "legacy":
        verify_file(root, "legacy-resource.json",
                    data["profiles"][profile]["compiler_profile"]["sha256"])
        weights_root = safe_file(root, "legacy-weights")
        index = verify_file(weights_root, "output.sha256", inputs["weights_index_sha256"])
        rows = verify_index(weights_root, index, expected=inputs["weights_count"], weights_only=True)
        require(rows["generated/calibration.json"] == inputs["calibration_sha256"],
                "calibration hash differs from independently pinned identity")
    graphs = safe_file(root, "graphs")
    for name, digest in {**inputs["onnx"], **(inputs["onnx_external_data"] or {})}.items():
        if digest is not None:
            verify_file(graphs, name, digest)


def verify_deployment(data, root, profile):
    runtime = data["profiles"][profile]["runtime"]
    names = data["runtime_artifact_names"]
    files = {}
    for name, artifact in names.items():
        if runtime.get(name) is not None:
            files[name] = verify_file(root, artifact, runtime[name])
    if "build_inputs" in files:
        verify_index(root, files["build_inputs"])
    if "quantized_inputs" in files:
        verify_index(root, files["quantized_inputs"])
    if "images" in files:
        images = read_json(files["images"])
        require(images["schema_version"] == "algo1-control-images/1", "wrong control-image schema")
        require("topology" in files, "control images require a pinned topology")
        target = read_json(files["topology"])["program_target"]
        controllers = target["controllers"]
        require(bool(target["topology_id"]) and images["topology_id"] == target["topology_id"],
                "control images target a different topology")
        require(set(images["source"]) == {"ir_sha256", "hardware_sha256", "plan_sha256"},
                "incomplete control-image source identity")
        for name, digest in images["source"].items():
            check_sha(digest, name)
        entries = images["images"]
        require({image["controller"] for image in entries} == set(controllers)
                and len(entries) == len(controllers), "missing or duplicate control images")
        require(sum(item["level"] == "mother" for item in controllers.values()) == 1
                and any(item["level"] == "local" for item in controllers.values()),
                "expected a mother controller and at least one local controller")
        used_paths = set()
        for image in entries:
            controller = controllers[image["controller"]]
            require(image["level"] == controller["level"] and image["abi"] == controller["abi"],
                    f"wrong image ABI or controller level: {image['controller']}")
            check_sha(image["sha256"], image["path"])
            path = verify_file(root, image["path"], image["sha256"])
            require(path not in used_paths, f"reused control image: {path}")
            used_paths.add(path)
            require(type(image["bytes"]) is int and path.stat().st_size == image["bytes"] > 0,
                    f"wrong image length: {path}")


def blockers(data, profile):
    checks = {
        **{f"server.{key}": data["server"][key] for key in
           ("host_key_fingerprint", "verified_checkpoint_path", "verified_toolchain_path")},
        **{f"onnx.{name}": digest for name, digest in data["historical_inputs"]["onnx"].items()},
        "onnx.external_data_inventory": data["historical_inputs"]["onnx_external_data"],
        **{f"{profile}.runtime.{name}": value for name, value in
           data["profiles"][profile]["runtime"].items()},
    }
    return [key for key, value in checks.items() if value is None]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--profile", choices=PROFILES, default="legacy")
    parser.add_argument("--assets", type=Path, help="staged checkpoint, reference, weights and graphs")
    parser.add_argument("--deployment", type=Path, help="staged runtime artifacts for the chosen profile")
    args = parser.parse_args()
    try:
        data = read_json(args.manifest)
        validate_manifest(data)
        print("PASS: manifest structure and pinned identifiers")
        if args.assets:
            verify_inputs(data, args.assets.resolve(), args.profile)
            print("PASS: verified staged inputs with available pins")
        if args.deployment:
            verify_deployment(data, args.deployment.resolve(), args.profile)
            print("PASS: verified staged deployment files with available pins")
        missing = blockers(data, args.profile)
        if not args.assets:
            missing.append("verified staged assets (--assets)")
        if not args.deployment:
            missing.append("verified staged deployment (--deployment)")
        if missing:
            for name in missing:
                print(f"PENDING: {name}")
            print("BLOCKED: submission preflight")
            return 2
        print("PASS: submission preflight")
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
