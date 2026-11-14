"""Run a manifest of independent native TLM experiments using the existing replay."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
INPUTS = ("program", "memory", "dram_library", "dram_config", "deployment_sha256")


def commands(manifest, output, selected=()):
    spec = json.loads(manifest.read_bytes())
    if set(spec) != {"inputs", "cases"} or not spec["cases"]:
        raise ValueError("expected inputs and a nonempty cases object")
    defaults = spec["inputs"]
    if set(defaults) - set(INPUTS):
        raise ValueError("unexpected default input")
    if set(selected) - spec["cases"].keys():
        raise ValueError("unknown case name")

    def path(value):
        return str((manifest.parent / value).resolve())

    def digest(value):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("expected a lowercase SHA-256 digest")
        return value

    for name, case in spec["cases"].items():
        if selected and name not in selected:
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise ValueError("case names must be lowercase directory names")
        overrides = case.get("inputs", {})
        inputs = {**defaults, **overrides}
        if set(inputs) != set(INPUTS):
            raise ValueError(f"{name}: missing or unknown input")
        mode = case["mode"]
        width = case.get("sram_port_bits", 128)
        window = case.get("kv_read_window", 1)
        budget = case.get("dma_fabric_budget", False)
        capture = case.get("capture_first_layer", False)
        pipeline = case.get("pipeline_memory", False)
        weight_fetch = case.get("rtl_weight_fetch", False)
        attention_pipeline = case.get("attn_sram_pipeline", False)
        response_slots = case.get("kv_response_slots", 0)
        value_fetch = case.get("av_value_fetch", "legacy")
        if (type(width) is not int or width not in (128, 512) or
                type(window) is not int or window not in range(1, 33) or
                any(type(flag) is not bool for flag in
                    (budget, capture, pipeline, weight_fetch, attention_pipeline))):
            raise ValueError(f"{name}: invalid port width, window or boolean")
        if type(response_slots) is not int or (response_slots and not window < response_slots <= 64):
            raise ValueError(f"{name}: invalid KV response slot count")
        if value_fetch not in ("legacy", "selected", "paired", "paired-ping-pong"):
            raise ValueError(f"{name}: invalid AV value fetch mode")
        if value_fetch == "paired-ping-pong" and not pipeline:
            raise ValueError(f"{name}: paired AV ping-pong requires the memory pipeline")
        if attention_pipeline and (not pipeline or not response_slots):
            raise ValueError(f"{name}: ATT1 SRAM pipeline requires memory pipeline and KV response slots")
        mode_options = {
            "decode": {"kv_binding", "kv_sha256"},
            "prefill": {"prefill_tokens"},
            "checkpoint": {"checkpoint_pages", "capture_first_layer"},
            "request": set(),
        }
        common = {"mode", "sram_port_bits", "dma_fabric_budget", "kv_read_window", "inputs",
                  "pipeline_memory", "rtl_weight_fetch", "attn_sram_pipeline", "kv_response_slots",
                  "av_value_fetch"}
        if mode not in mode_options or set(case) - common - mode_options[mode]:
            raise ValueError(f"{name}: options do not match the selected mode")
        required = {"decode": {"kv_binding", "kv_sha256"}, "checkpoint": {"checkpoint_pages"}}
        if required.get(mode, set()) - case.keys():
            raise ValueError(f"{name}: missing options for {mode}")

        out = output / name
        replay = [sys.executable, "-B", str(HERE / "run_native_tlm_request.py"),
                  *(path(inputs[key]) for key in INPUTS[:-1]), str(out),
                  digest(inputs["deployment_sha256"]), "--sram-port-bits", str(width),
                  "--kv-read-window", str(window)]
        if budget:
            replay.append("--dma-fabric-budget")
        for enabled, flag in ((pipeline, "--pipeline-memory"), (weight_fetch, "--rtl-weight-fetch"),
                              (attention_pipeline, "--attn-sram-pipeline")):
            if enabled:
                replay.append(flag)
        if response_slots:
            replay.extend(("--kv-response-slots", str(response_slots)))
        if value_fetch != "legacy":
            replay.extend(("--av-value-fetch", value_fetch))
        audit = []
        if mode == "decode":
            replay.extend(("--decode-kv-binding", path(case["kv_binding"]),
                           "--decode-kv-sha256", digest(case["kv_sha256"])))
            audit = [str(HERE / "audit_native_decode_timing.py"), str(out)]
        elif mode == "prefill":
            tokens = case.get("prefill_tokens", 2)
            if type(tokens) is not int or tokens not in (1, 2):
                raise ValueError(f"{name}: prefill_tokens must be 1 or 2")
            replay.extend(("--prefill-tokens", str(tokens)))
            audit = [str(HERE.parents[2] / "work/YUZE-LU/234/native-sram-width/audit_prefill.py"),
                     str(out), str(tokens), "--sram-port-bits", str(width)]
        elif mode == "checkpoint":
            pages = case["checkpoint_pages"]
            if type(pages) is not int or pages < 1:
                raise ValueError(f"{name}: checkpoint_pages must be positive")
            replay.extend(("--checkpoint-pages", str(pages)))
            if capture:
                replay.append("--capture-first-layer")
        yield name, out, replay, [sys.executable, "-B", *audit] if audit else []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = list(commands(args.manifest.resolve(), args.output_root.resolve(), args.case))
    if args.dry_run:
        print(json.dumps({name: {"replay": replay, "audit": audit}
                          for name, _, replay, audit in plan}, indent=2))
        return
    for _, out, _, _ in plan:
        if out.exists():
            parser.error(f"output already exists: {out}")
    args.output_root.mkdir(parents=True, exist_ok=True)
    for _, out, replay, audit in plan:
        subprocess.run(replay, check=True)
        if audit:
            result = subprocess.check_output(audit)
            (out / "timing-audit.json").write_bytes(result)


if __name__ == "__main__":
    main()
