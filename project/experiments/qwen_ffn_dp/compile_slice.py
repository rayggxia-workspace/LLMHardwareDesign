"""Constraint-aware mapping for a two-lane P16 FFN projection/gate slice."""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
from pathlib import Path


P16_ABI = "0485ed84dd13d8711c88609668cf0a903a006773"
# Word addresses. Four K8 tiles each use one aligned A line and one aligned B line.
A, B, GATE, UP, MID = 0, 16, 32, 33, 34
WORDS = 1024
K = 2560


@dataclass(frozen=True)
class State:
    gate_ready: int = -1
    up_ready: int = -1
    up_owner: int = -1
    m_free: tuple = (0, 0)


@dataclass(frozen=True)
class Plan:
    up_owner: int
    gate_ready: int
    up_ready: int
    mid_ready: int
    required_bundles: tuple
    cost: int


def finish(state, manifest):
    cross = state.up_owner == 1
    bundle = manifest["cross_bundle"]
    if cross and bundle["access"] == "proven_impossible":
        return None
    transfer = bundle["estimated_cycles"] if cross else 0
    ready = max(state.gate_ready, state.up_ready + transfer)
    done = ready + manifest["gate_cycles"]
    return Plan(state.up_owner, state.gate_ready, state.up_ready, done,
                (bundle["id"],) if cross else (),
                done + (bundle["incremental_cost"] if cross and not bundle["prewired"] else 0))


def dp(manifest):
    """Evaluate the acyclic frontier at each projection placement decision.

    Compile order is gate then up. The recorded per-instance clocks allow
    concurrently placing up on P1 even though it is visited second.
    """
    front = {State()}
    for op, instances in (("gate", (0,)), ("up", (0, 1))):
        successor = set()
        for state, instance in itertools.product(front, instances):
            clocks = list(state.m_free)
            clocks[instance] += manifest["projection_cycles"][op]
            successor.add(State(clocks[instance] if op == "gate" else state.gate_ready,
                                clocks[instance] if op == "up" else state.up_ready,
                                instance if op == "up" else state.up_owner, tuple(clocks)))
        front = successor
    plans = [finish(state, manifest) for state in front]
    return sorted((p for p in plans if p is not None), key=lambda p: (p.cost, p.up_owner))


def exhaustive(manifest):
    """Independent two-placement schedule oracle with gate dispatched first."""
    g, u = (manifest["projection_cycles"][op] for op in ("gate", "up"))
    h = manifest["gate_cycles"]
    expected = [Plan(0, g, g + u, g + u + h, (), g + u + h)]
    b = manifest["cross_bundle"]
    if b["access"] != "proven_impossible":
        end = max(g, u + b["estimated_cycles"]) + h
        expected.append(Plan(1, g, u, end, (b["id"],),
                             end + (0 if b["prewired"] else b["incremental_cost"])))
    return sorted(expected, key=lambda p: (p.cost, p.up_owner))


def program(plan, manifest):
    """Emit explicit service operations for the control adapter, with true dependencies."""
    block = f"P{plan.up_owner}"
    mother = [{"op": "call", "block": "P0", "entry": "gate"}]
    if plan.up_owner:
        mother.append({"op": "reserve", "block": "P0", "word": UP})
    mother.extend([
        {"op": "call", "block": block, "entry": "up"},
        {"op": "wait", "event": "gate_stored"},
        {"op": "wait", "event": "up_stored" if not plan.up_owner else "up_rx_stored"},
        {"op": "call", "block": "P0", "entry": "mid"},
        {"op": "wait", "event": "mid_stored"},
        {"op": "end"},
    ])
    local = {
        "P0": {
            "gate": [{"op": "project", "weight": "gate_proj", "dst": GATE,
                      "event": "gate_stored"}],
            "mid": [{"op": "gate", "a": GATE, "b": UP, "dst": MID, "event": "mid_stored"}],
        }
    }
    local.setdefault(block, {})["up"] = [
        {"op": "project", "weight": "up_proj", "dst": UP, "event": "up_stored"}]
    if plan.up_owner:
        local[block]["up"].append({"op": "copy", "src": UP, "dst_block": "P0", "dst": UP,
                                  "release_after": "up_rx_stored"})
    return {
        "abi": P16_ABI, "base_id": manifest["base_id"], "model": manifest["model"],
        "word_bytes": 16, "capacity_words": WORDS, "valid_s16_lanes": 2,
        "scratch": {"a_words": list(range(A, A + 16)), "b_words": list(range(B, B + 16)),
                    "gate_word": GATE, "up_word": UP, "mid_word": MID},
        "k": K, "k_segment": 32, "plan": asdict(plan), "mother": mother, "local": local,
        "bundles": [manifest["cross_bundle"]] if plan.required_bundles else [],
    }


def apply_feedback(manifest, feedback):
    if feedback["base_id"] != manifest["base_id"]:
        raise ValueError("feedback refers to a different physical base")
    bundle = manifest["cross_bundle"]
    if feedback["bundle_id"] != bundle["id"]:
        raise ValueError("feedback refers to a different bundle")
    evidence = feedback["evidence_sha256"]
    if len(evidence) != 64 or any(c not in "0123456789abcdef" for c in evidence):
        raise ValueError("feedback needs a report SHA-256")
    if feedback["result"] == "proven_impossible":
        if feedback["kind"] != "pin_access_certificate":
            raise ValueError("a router failure or timeout cannot prove infeasibility")
        bundle["access"] = feedback["result"]
    elif feedback["result"] == "penalty":
        penalty = feedback["incremental_cost"]
        if not isinstance(penalty, int) or penalty < 0:
            raise ValueError("penalty must be a nonnegative integer")
        bundle["incremental_cost"] += penalty
    else:
        raise ValueError("unknown feedback result")
    manifest["route_feedback"] = feedback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--feedback", type=Path)
    args = parser.parse_args()
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    if args.feedback:
        apply_feedback(manifest, json.loads(args.feedback.read_bytes()))
    candidates = dp(manifest)
    if candidates != exhaustive(manifest):
        raise RuntimeError("DP differs from exhaustive oracle")
    artifact = program(candidates[0], manifest)
    artifact["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    artifact["candidates"] = [asdict(plan) for plan in candidates]
    if args.feedback:
        artifact["route_feedback"] = manifest["route_feedback"]
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

