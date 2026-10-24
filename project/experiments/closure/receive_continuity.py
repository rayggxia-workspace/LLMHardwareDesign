"""Independent transitive receipt for Falcon complete-branch continuity.

Requires an already independently replayed baseline. Exact bytes and every
intermediate checkpoint hash are then checked against that numerical evidence;
this tool does not repeat identical large integer arithmetic per chunk policy.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from audit_io import need, load_json, save_json, sha, descriptor, verify_manifest, replace_artifact_hash
from receive_falcon import array_hash, load_arrays, audit_runtime_source


def complete_descriptor(state_hash, units, history, epoch, position, contract):
    record = {"owner": "layer0.mamba.integer", "state_sha256": state_hash,
              "units_sha256": array_hash(units), "conv_sha256": array_hash(history),
              "units": units.tolist(), "epoch": int(epoch), "version": int(position),
              "position": int(position), "contract": contract}
    record["checksum"] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return record


def history_at(projected, position, inner, state_size):
    width = inner + 2 * state_size
    need(projected.dtype == np.int32, "true integer projected history")
    history = np.zeros((width, 4), np.int32)
    rows = projected[max(0, position - 4):position, inner:inner + width]
    if len(rows):
        history[:, -len(rows):] = rows.T
    return history


def verify(result, baseline, baseline_receipt, compiled, producer_source, int_source):
    result, baseline, baseline_receipt, compiled = map(Path, (result, baseline, baseline_receipt, compiled))
    man, checked = verify_manifest(result, statuses=("EXECUTED",))
    bm, bc = verify_manifest(baseline, statuses=("EXECUTED",))
    cm, cc = verify_manifest(compiled, statuses=("EXECUTED",))
    need(man["schema"] == "falcon-complete-continuity-v1", "continuity artifact schema")
    need(man["source"]["falcon_resume_sha256"] == sha(producer_source)
         and man["source"]["falcon_int_sha256"] == sha(int_source)
         and man["integer_source_sha256"] == sha(int_source), "continuity source binding")
    source_audit = audit_runtime_source(int_source)
    receipt = load_json(baseline_receipt)
    need(receipt["status"] == "PASS" and receipt["mode"] == "full"
         and receipt["committed_tokens"] == receipt["input_tokens"] == 72
         and receipt["producer_manifest"] == descriptor(baseline / "manifest.json")
         and receipt["artifacts"] == bc and receipt["compiled_artifacts"] == cc,
         "independently verified complete baseline binding")
    report, transaction = load_json(result / "report.json"), load_json(result / "transactions.json")
    br, bt = load_json(baseline / "report.json"), load_json(baseline / "transactions.json")
    z, old, snapshots = load_arrays(result / "runtime.npz"), load_arrays(baseline / "runtime.npz"), load_arrays(result / "checkpoints.npz")
    need(report["baseline_manifest_sha256"] == sha(baseline / "manifest.json")
         and report["compiled_manifest_sha256"] == br["compiled_manifest_sha256"] == sha(compiled / "manifest.json"),
         "numeric/compiled provenance")
    need(set(z) == set(old), "complete identical integer stage set")
    comparisons = {row["array"]: row for row in report["integer_arrays"]}
    need(set(comparisons) == set(z), "complete comparison records")
    for name, value in z.items():
        need(value.dtype == old[name].dtype and value.shape == old[name].shape
             and np.array_equal(value, old[name]), "full-chain numerical equality " + name)
        row = comparisons[name]
        need(row["equal"] is True and row["runtime_sha256"] == array_hash(value)
             and row["baseline_sha256"] == array_hash(old[name]), "recorded stage equality " + name)
    need(transaction["state_sha256"] == bt["state_sha256"], "independent per-token state history")
    bits, policy = br["state_bits"], br["policy"]
    contract = {"compiled_manifest_sha256": sha(compiled / "manifest.json"), "bits": bits,
                "policy": policy, "mode": "full", "sequence": "Issue70.cal16/eval72",
                "heads": 32, "dim": 128, "n": 256}
    need(transaction["contract"] == contract and len(transaction["tokens"]) == 72,
         "complete branch transaction contract")
    projected, units = z["projected_q12"], old["state_units_trace"]
    need(units.shape == (73, 32) and units.dtype == np.int16, "complete unit history")
    descriptors = []
    for position in range(73):
        epoch = 0 if position == 0 else bt["tokens"][position - 1]["after"]["epoch"]
        descriptors.append(complete_descriptor(bt["state_sha256"][position], units[position],
                                              history_at(projected, position, 4096, 256), epoch, position, contract))
    rescale_events = 0
    for token, record in enumerate(transaction["tokens"]):
        need(record["token"] == token and record["before"] == descriptors[token]
             and record["after"] == descriptors[token + 1] and record["branch_published"] is True,
             "atomic complete branch ownership/publication")
        private = copy.deepcopy(record["private_R_transactions"])
        need(len(private) == 1 and private[0]["token"] == 0, "single private current-token update")
        private[0]["token"] = token
        need(private[0] == bt["tokens"][token], "private R same numerical transaction")
        private_events = copy.deepcopy(record["private_R_rescale_events"])
        for event in private_events:
            need(event["token"] == 0 and event["published"] is False, "unpublished private recode")
            event["token"] = token
        expected = [event for event in bt["rescale_events"] if event["token"] == token]
        need(private_events == expected, "same causal recode history")
        rescale_events += len(private_events)
    schedule = report["schedule"]
    need(schedule in ("full", "chunk8", "chunk16", "prefill64decode1"), "continuity schedule")
    positions = ({72} if schedule == "full" else set(range(8, 73, 8)) | {72} if schedule == "chunk8"
                 else set(range(16, 73, 16)) | {72} if schedule == "chunk16" else set(range(64, 73)))
    need([d["position"] for d in transaction["checkpoints"]] == sorted(positions), "exact chunk checkpoint boundaries")
    keys = set()
    for d in transaction["checkpoints"]:
        p = int(d["position"])
        need(d == descriptors[p], "complete checkpoint descriptor")
        for suffix in ("state", "units", "conv"):
            keys.add(f"at{p}.{suffix}")
        state, u, history = (snapshots[f"at{p}.{suffix}"] for suffix in ("state", "units", "conv"))
        need(state.shape == (32, 128, 256) and state.dtype == np.dtype(f"int{bits}")
             and array_hash(state) == bt["state_sha256"][p], "checkpoint matches independently replayed state")
        need(u.dtype == np.int16 and np.array_equal(u, units[p])
             and history.dtype == np.int32 and np.array_equal(history, history_at(projected, p, 4096, 256)),
             "checkpoint units/complete conv history")
    need(set(snapshots) == keys, "complete checkpoint physical arrays")
    need(report["status"] == "PASS_INTEGER_CONTINUITY" and report["committed"] == 72
         and report["all_integer_arrays_equal"] is True and report["state_hashes_equal_to_frozen_baseline"] is True
         and report["state_bits"] == bits and report["policy"] == policy
         and report["final_epoch"] == descriptors[-1]["epoch"]
         and report["rescale_events"] == rescale_events
         and report["published_state_saturations"] == br["published_state_saturations"], "continuity outcome")
    return {"status": "PASS", "schedule": schedule, "state_bits": bits, "policy": policy,
            "complete_integer_arrays": len(z), "state_positions_checked": 73,
            "private_transactions_checked": 72, "complete_checkpoints": len(positions),
            "baseline_receipt": descriptor(baseline_receipt), "runtime_source_audit": source_audit,
            "baseline_manifest": descriptor(baseline / "manifest.json"), "artifacts": checked,
            "limits": ["Transitive numerical proof requires frozen independently replayed baseline; source operators are not rerun for every identical chunk policy",
                       "Checkpoint/atomic publication descriptors checked; no RTL, native kernel speed, application quality or hardware failure-injection proof"]}


def main():
    ap = argparse.ArgumentParser(__doc__)
    for name in ("result", "baseline", "baseline-receipt", "compiled", "producer-source", "int-source", "binding", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--skip-negatives", action="store_true")
    args = ap.parse_args()
    need(not args.out.exists(), "refuse output overwrite")
    binding = load_json(args.binding)
    for name in ("receive_continuity", "receive_falcon", "audit_io", "integer_oracle"):
        need(binding.get(name + "_sha256") == sha(Path(__file__).with_name(name + ".py")), "receiver dependency " + name)
    args.out.mkdir(parents=True)
    receipt = verify(args.result, args.baseline, args.baseline_receipt, args.compiled, args.producer_source, args.int_source)
    receipt["receiver"] = binding
    receipt["semantic_negatives"] = [] if args.skip_negatives else negatives(
        args.result, args.baseline, args.baseline_receipt, args.compiled, args.producer_source, args.int_source, args.out)
    if args.skip_negatives:
        receipt["status"] = "PARTIAL_NO_NEGATIVES"
    save_json(args.out / "receipt.json", receipt)
    print(receipt["status"], receipt["schedule"], flush=True)


def negatives(result, baseline, baseline_receipt, compiled, producer_source, int_source, out):
    receipts = []
    for name in ("state", "conv", "owner", "private_unit"):
        folder = Path(out) / ("negative-" + name)
        shutil.copytree(result, folder)
        if name in ("state", "conv"):
            arrays = load_arrays(folder / "checkpoints.npz")
            key = next(k for k in sorted(arrays) if k.endswith("." + name))
            arrays[key].flat[0] ^= 1
            np.savez_compressed(folder / "checkpoints.npz", **arrays)
            replace_artifact_hash(folder, "checkpoints.npz")
        else:
            data = load_json(folder / "transactions.json")
            if name == "owner":
                d = data["tokens"][0]["after"]
                d["owner"] = "another.owner"
                # Recompute the object's own checksum as well as artifact SHA;
                # owner identity must be checked against the semantic contract.
                unsigned = {k: v for k, v in d.items() if k != "checksum"}
                d["checksum"] = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            else:
                data["tokens"][1]["private_R_transactions"][0]["attempts"][0]["trial_units"][0] += 1
            save_json(folder / "transactions.json", data)
            replace_artifact_hash(folder, "transactions.json")
        verify_manifest(folder, statuses=("EXECUTED",))
        try:
            verify(folder, baseline, baseline_receipt, compiled, producer_source, int_source)
        except (ValueError, AssertionError) as error:
            receipts.append({"case": name, "artifact_hash_rewritten": True,
                             "artifact_hash_layer_passed": True, "semantic_rejected": True,
                             "reason": str(error), "mutated_manifest": descriptor(folder / "manifest.json")})
        else:
            raise ValueError("continuity semantic negative accepted: " + name)
    return receipts


if __name__ == "__main__":
    main()
