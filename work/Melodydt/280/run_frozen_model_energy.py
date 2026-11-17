"""Execute the accepted plan unchanged and require byte-identical replay outputs."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

from fast_qwen3_short import BatchedClock
from fast_tlm_replay import DramBridge
import native_tlm_projection
import pr272_native_projection
from projection_math import NativeAccumulator
import qwen3_short as replay
from six_model_observation import ModelObservation
from ddr_window_energy import evaluate
from qwen3_dma_windows import FIELDS, window


def load(path):
    return json.loads(path.read_bytes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("baseline", "library", "ini", "output"):
        p.add_argument(key, type=Path)
    a = p.parse_args()
    frozen = load(a.baseline / "result.json")
    assets = a.baseline / "assets"
    raw = (assets / "plan.json").read_bytes()
    if sha256(raw).hexdigest() != frozen["plan_sha256"]:
        raise ValueError("unverified frozen plan")
    plan = json.loads(raw)
    if not plan.get("three_p") or frozen["weight_window"] != 4 or frozen["pr272_profile"] != "combined":
        raise ValueError("expected accepted three-P combined benchmark")
    arithmetic = NativeAccumulator(Path(os.environ["SHORT_PROJECTION_MATH"]))
    native_tlm_projection.accumulate = arithmetic
    pr272_native_projection.accumulate = arithmetic
    replay.Clock, replay.Dram = BatchedClock, DramBridge
    a.output.mkdir()
    execution = replay.Execution(plan, assets, a.library, a.ini, a.output, 4, "combined")
    observation = ModelObservation(execution)
    result = execution.run(trace_layers=True)
    # These are compiler/launcher metadata, not execution results.
    for key in ("plan_sha256", "model", "ffn_context_cache", "compact_kv64", "tiled_attention128", "workload"):
        if key in frozen:
            result[key] = frozen[key]
    result["history_payload"] = "live FP32" if "representative_history" in plan else "zeros"
    result["history_beats"] = execution.memory.history_beats
    if "residual_fraction_bits" in frozen:
        result["residual_fraction_bits"] = execution.residual_fraction_bits
    result["ffn_by_target"] = {site: dict(unit.stats) for site, unit in execution.ffn_lane_proj.items()}
    if execution.moe_lane_down:
        result["expert_down_by_target"] = {site: dict(unit.stats) for site, unit in execution.moe_lane_down.items()}
    if "representative_history" in plan:
        if not execution.memory.history_beats:
            raise ValueError("history was not consumed")
        result["history_source_sha256"] = plan["representative_history"]["source_sha256"]
    result = json.loads(json.dumps(result))
    changed = [key for key in sorted(set(result) | set(frozen)) if result.get(key) != frozen.get(key)]
    if changed:
        (a.output / "rejected-result.json").write_text(json.dumps(result, indent=2) + "\n")
        raise ValueError("frozen result changed: " + str(changed))
    (a.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    # Every residual, logit and layer snapshot named in the original run is checked.
    for path in a.baseline.iterdir():
        if path.suffix in (".bin", ".q16", ".s32") or path.name == "layer-trace.json":
            if path.read_bytes() != (a.output / path.name).read_bytes():
                raise ValueError("frozen numerical output changed: " + path.name)
    energy = evaluate(a.output, a.baseline)
    observation.write(a.output / "component-observation.json")
    names = ("start", "prefill_end", "end") if result["mode"] == "prefill" else ("start", "retire_1", "retire_2", "end")
    snapshots = {name: load(a.output / ("energy-" + name + ".json")) for name in names}
    for snap in snapshots.values():
        dma = snap["dma_observation"]
        for rows in dma["channels"]:
            for row in rows:
                if set(row) != set(FIELDS) or min(row.values()) < 0 or row["submitted"] != row["queued"] + row["accepted"] or row["accepted"] != row["inflight"] + row["completed"]:
                    raise ValueError("DMA cumulative accounting failed")
    for direction, field in enumerate(("reads", "writes")):
        rows = [row[direction] for row in snapshots["end"]["dma_observation"]["channels"]]
        if any(row["inflight"] or row["queued"] for row in rows) or sum(row["completed"] for row in rows) != result["ddr"][field]:
            raise ValueError("DMA terminal accounting failed")
    if result["mode"] == "prefill":
        transport = {"prefill": window(snapshots["start"], snapshots["prefill_end"], 2)}
    else:
        transport = {"first_token": window(snapshots["start"], snapshots["retire_1"], 1),
                     "decode": window(snapshots["retire_1"], snapshots["retire_2"], 1)}
    (a.output / "ddr-window-energy.json").write_text(json.dumps(energy, indent=2) + "\n")
    (a.output / "dma-windows.json").write_text(json.dumps(transport, indent=2) + "\n")
    (a.output / "acceptance.json").write_text(json.dumps({"passed": True, "baseline": str(a.baseline),
        "plan_sha256": frozen["plan_sha256"], "complete_result_equal": True, "numerical_files_equal": True,
        "ddr_terminal_reconciled": True, "sram_observer_reconciled": True}, indent=2) + "\n")
    print("MODEL_ENERGY_STAGE_PASS", frozen["model"], result["mode"], flush=True)


if __name__ == "__main__":
    main()
