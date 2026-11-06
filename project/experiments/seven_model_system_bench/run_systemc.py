
"""Replay the seven fixed PR #154 checkpoints and audit against its sealed results."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def replay(name, reference, binary, tools, out, checkpoints):
    run = out / name
    run.mkdir()
    checkpoint = checkpoints / Path(reference["checkpoint"]).name
    started = time.monotonic()
    result = {"model": name, "checkpoint": str(checkpoint), "passed": False}
    try:
        inputs = {file: sha256(checkpoint / file) for file in reference["checkpoint_inputs"]}
        if inputs != {file: item["sha256"] for file, item in reference["checkpoint_inputs"].items()}:
            raise ValueError("frozen checkpoint checksum mismatch")
        result["input_sha256"] = inputs
        env = dict(os.environ, LLM_PRECISE_ADAPTER="1", LLM_BLOCK_SCALES="1",
                   LLM_ACCURATE_SILU="1", LLM_LINK="1", LLM_LINK_WIDTH_BYTES="64",
                   LLM_LINK_QUEUE_PACKETS="1", LLM_FLOW_DIR=str(run))
        for key in ("LLM_LINK_CORRUPT", "LLM_LINK_DROP_RESPONSE", "LLM_FIRST_LAYER_ONLY",
                    "LLM_TRACE_LAYER", "LLM_NORM_FUSED", "LLM_SSM_BLOCK_SCALES"):
            env.pop(key, None)
        with (run / "inference.log").open("w") as log:
            subprocess.run([str(binary), str(checkpoint), str(run)], env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        with (run / "flow.log").open("w") as log:
            subprocess.run(["python3", "-B", str(tools / "analyze_flow.py"), str(run)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        counts = re.findall(
            r"CD_EXECUTED windows=(\d+) words=(\d+) bursts=(\d+) C_submitted=(\d+) C_completed=(\d+)",
            (run / "inference.log").read_text())
        if len(counts) != 1 or list(counts[0]) != reference["cd_counts"]:
            raise ValueError("C/D activity differs from the frozen reference")
        outputs = {file: sha256(run / file) for file in (
            "systemc_hidden.bin", "systemc_logits.bin", "flow-summary.json",
            "systemc_receipt.json", "cd-payload.json", "inference.log")}
        for file in ("systemc_hidden.bin", "systemc_logits.bin"):
            if outputs[file] != reference["outputs"][file]["sha256"]:
                raise ValueError("frozen numerical output mismatch: " + file)
        result.update(
            passed=True,
            frozen_numerical_gate=reference["numerical_gate"],
            c_d=dict(zip(("windows", "words", "bursts", "submitted", "completed"), map(int, counts[0]))),
            receipt=read_json(run / "systemc_receipt.json"),
            flow={key: value for key, value in read_json(run / "flow-summary.json").items()
                  if key not in ("edges", "operations_by_program", "longest_lived_values", "unmapped_host_sources")},
            output_sha256=outputs,
            checkpoint_bytes={file: (checkpoint / file).stat().st_size for file in inputs},
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        result["error"] = str(exc)
    result["host_elapsed_seconds"] = round(time.monotonic() - started, 3)
    write_json(run / "benchmark.json", result)
    print(name, "PASS" if result["passed"] else result["error"], flush=True)
    return name, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("binary", type=Path)
    parser.add_argument("frozen", type=Path)
    parser.add_argument("checkpoints", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    args.out.mkdir()
    reference = read_json(args.frozen)["models"]
    if len(reference) != 7 or not all(x["passed"] for x in reference.values()):
        raise ValueError("expected seven passing frozen references")
    tools = args.source / "project/systemc/llm/tools"
    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(replay, name, prior, args.binary, tools, args.out, args.checkpoints)
                   for name, prior in reference.items()]
        for future in pending:
            name, result = future.result()
            results[name] = result
    passed = all(item["passed"] for item in results.values())
    write_json(args.out / "systemc-summary.json", {
        "passed": passed, "job_id": os.environ.get("SLURM_JOB_ID"),
        "binary_sha256": sha256(args.binary), "frozen_receipt_sha256": sha256(args.frozen),
        "models": results,
    })
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
