"""Merge seven already independent service audit receipts without replaying DAGs.

Inputs remain read-only. This verifies byte/source/coverage/metric provenance and
cross-shard label-only equality, never executes producer arithmetic or scheduling.
"""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import time


ORGANIZATIONS = ("shared8", "shared2_6", "shared4_4", "shared6_2", "split2_6", "split4_4", "split6_2")
GRID = dict(ext_profiles=[1, 16], tiles=[16, 32], norm_routes=["reread", "spill"], strategies=["fifo", "critical"])
RECEIVER_SHA256 = "325a3668f6855019b43f273502e4ddb033e5f5422656c8bd070eaf777b492e75"
SCHEMA = "issue68-service/1"


def require(value, label):
    if not value:
        raise AssertionError(label)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def descriptor(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "regular immutable evidence file")
    return dict(bytes=path.stat().st_size, sha256=sha(path))


def checked_manifest(folder, expected_config):
    folder = Path(folder)
    manifest = load(folder / "manifest.json")
    require(manifest.get("schema") == SCHEMA and manifest.get("config") == expected_config,
            "complete declared logical/shard grid")
    checked = {}
    for name, wanted in manifest.get("artifacts", {}).items():
        require(isinstance(name, str) and Path(name).name == name and "\\" not in name, "safe artifact basename")
        checked[name] = descriptor(folder / name)
        require(checked[name] == {key: wanted[key] for key in ("bytes", "sha256")}, "artifact SHA/bytes " + name)
    require("metrics.json" in checked, "indexed metrics")
    metrics = load(folder / "metrics.json")
    require(metrics.get("schema") == SCHEMA and metrics.get("status") == "PASS_CONDITIONAL_SCHEDULE"
            and metrics.get("source") == manifest.get("source"), "executed metrics/source binding")
    return manifest, metrics, checked


def expected_task(suite):
    require(suite in ("native", "legacy"), "suite")
    return "native.evaluation.S32.D31.guard_rescale" if suite == "native" else "legacy.layer0-end8192.S32.D31.guard_rescale"


def metric_index(metrics, organizations, suite):
    indexed, row_keys, fingerprints, contracts = {}, set(), set(), set()
    task = expected_task(suite)
    for row in metrics.get("results", []):
        key = (row["organization"], row["ext_ii"], row["tile"], row["norm_route"])
        require(key not in row_keys and row["task"] == task and row["state_bits"] == 32, "unique correct task/precision case")
        row_keys.add(key)
        fingerprints.add(row["task_fingerprint"])
        contracts.add(row["commit_contract"])
        choices = row["strategies"]
        require(len(choices) == 2 and {choice["strategy"] for choice in choices} == {"fifo", "critical"}, "both formal grid strategies")
        require(row["best"] == min(choices, key=lambda choice: (choice["cycles"], choice["strategy"])), "finite declared strategy minimum")
        for choice in choices:
            name = choice["witness"]
            require(name not in indexed and name.endswith(".json.gz"), "unique indexed gzip witness")
            require(type(choice["cycles"]) is int and choice["cycles"] > 0 and type(choice["nodes"]) is int and choice["nodes"] > 0,
                    "positive actual service metric")
            indexed[name] = dict(id=[task, row["organization"], row["tile"], row["norm_route"], row["ext_ii"], choice["strategy"]],
                task_fingerprint=row["task_fingerprint"], commit_contract=row["commit_contract"], cycles=choice["cycles"],
                operations=choice["nodes"], resident_bytes=choice["memory"], payload_bytes=choice["payload_bytes"], wire_bytes=choice["wire_bytes"])
    expected = set(itertools.product(organizations, GRID["ext_profiles"], GRID["tiles"], GRID["norm_routes"]))
    require(row_keys == expected and len(metrics["results"]) == 8 * len(organizations), "complete formal case coverage")
    require(len(indexed) == 16 * len(organizations) and len(fingerprints) == len(contracts) == 1,
            "same exact task fingerprint/commit contract")
    return indexed


def audit_cases(audit, expected, receiver_binding, receiver_binding_sha, input_root, range_root):
    require(audit.get("status") == "PASS_INDEPENDENT_SERVICE", "independent shard audit PASS")
    source = audit.get("source", {})
    require(source.get("receive_service_sha256") == RECEIVER_SHA256
            == receiver_binding.get("receive_service_sha256") and source.get("commit") == receiver_binding.get("commit")
            and source.get("binding_sha256") == receiver_binding_sha, "frozen independent receiver source binding")
    require(audit.get("two_rounds") == dict(all_scientific_SHA_identical=True, artifacts=17, arithmetic_schedules_independent=1),
            "full two-round shard byte checks")
    require(audit.get("declared_strategies") == ["critical", "fifo"] and audit.get("complete_witnesses") == 16,
            "formal shard independent strategy/witness scope")
    require(audit.get("declared_source_root") == input_root and audit.get("range_root") == range_root
            and audit.get("norm_stage") == "norm03", "shard audit original numeric inputs")
    require(audit.get("quality_accepted") is False and audit.get("hardware_implemented") is False,
            "software audit versus quality/hardware scope")
    require(audit.get("shared_split_label_only_pairs") == 0
            and audit.get("shared_split_label_only_cycles_difference") is None, "single organization has no unexecuted cross-label comparison")
    negatives = audit.get("negative_checks", [])
    require(len(negatives) == 4 and {n["mutation"] for n in negatives} == {"dependency", "overlap", "capacity", "epoch"}
            and all(n.get("rewritten_SHA_passed") is True and n.get("status") == "REJECTED_INDEPENDENT_SEMANTICS" for n in negatives),
            "all four actual rehashed witness negative controls")
    seen = set()
    for case in audit.get("cases", []):
        name = case["witness"]
        require(name in expected and name not in seen, "unique covered audited witness")
        seen.add(name)
        for key, wanted in expected[name].items():
            require(case.get(key) == wanted, "independent audit/logical metric " + key)
        require(type(case.get("independent_lower_bound")) is int and 0 <= case["independent_lower_bound"] <= case["cycles"]
                and type(case.get("precedence_lower_bound")) is int and 0 <= case["precedence_lower_bound"] <= case["independent_lower_bound"],
                "declared-model independent lower bound")
        require(case.get("physical_claim") is False, "no target physical performance claim")
    require(seen == set(expected) and len(audit["cases"]) == 16, "complete independent shard witness coverage")
    return audit["cases"]


def cross_label(signatures, suite, cases=None):
    """Check all48 exact same-resource shared/split comparisons, no scheduler."""
    task = expected_task(suite)
    indexed = {}
    actual_cases = {tuple(case["id"]): case for case in cases} if cases is not None else None
    for org, records in signatures.items():
        expected_keys = set(itertools.product(GRID["tiles"], GRID["norm_routes"], GRID["ext_profiles"], GRID["strategies"]))
        if org == "shared8":
            require(records == [], "whole-pool profile outside label-only pairs")
            continue
        suffix = org.removeprefix("shared").removeprefix("split")
        seen = set()
        for record in records:
            key = record["key"]
            require(isinstance(key, list) and len(key) == 6 and key[0] == task and key[5] == suffix
                    and record["organizations"] == [org], "single-shard exact pair signature provenance")
            local = tuple(key[1:5])
            require(local in expected_keys and local not in seen, "unique complete pair configuration")
            seen.add(local)
            require(type(record["signature"]["cycles"]) is int and record["signature"]["cycles"] > 0,
                    "positive paired cycles")
            if actual_cases is not None:
                case_id = (task, org, key[1], key[2], key[3], key[4])
                require(case_id in actual_cases and record["signature"]["cycles"] == actual_cases[case_id]["cycles"],
                        "pair signature actual audited cycles")
            indexed[(org, local)] = record["signature"]
        require(seen == expected_keys, "complete16 signature configurations")
    pairs = []
    for suffix in ("2_6", "4_4", "6_2"):
        for tile, route, ext, strategy in itertools.product(GRID["tiles"], GRID["norm_routes"], GRID["ext_profiles"], GRID["strategies"]):
            local = (tile, route, ext, strategy)
            a, b = indexed[("shared" + suffix, local)], indexed[("split" + suffix, local)]
            require(a == b, "shared/split exact same-resource nodes/allocations/inventory/cycles")
            pairs.append(dict(suffix=suffix, tile=tile, norm_route=route, ext_ii=ext, strategy=strategy,
                              cycles=a["cycles"], signature=a, cycles_difference=0))
    require(len(pairs) == 48, "exact48 label-only comparisons")
    return pairs


def merge(root, suite, out, binding, receiver_binding_path=None):
    begin = time.monotonic()
    root, out = Path(root).resolve(), Path(out).resolve()
    require(root.is_dir() and not out.exists() and out.parent.is_dir(), "readable inputs/new output file")
    require(binding.get("merge_audits_sha256") == sha(__file__) and binding.get("commit"), "merge source binding")
    receiver_binding_path = Path(receiver_binding_path) if receiver_binding_path else root / "phase9" / "binding.json"
    receiver_binding, receiver_binding_sha = load(receiver_binding_path), sha(receiver_binding_path)
    require(receiver_binding.get("receive_service_sha256") == RECEIVER_SHA256 and receiver_binding.get("commit"),
            "known phase9 independent receiver")
    prefix = "n" if suite == "native" else "l"
    logical = []
    for number in (1, 2):
        folder = root / f"service-{suite}{number:02d}"
        m, metrics, artifacts = checked_manifest(folder, dict(GRID, lane_profiles=list(ORGANIZATIONS)))
        index = metric_index(metrics, ORGANIZATIONS, suite)
        require(set(artifacts) == {"metrics.json"} | set(index), "logical manifest all112 unique witnesses plus metrics")
        logical.append((folder, m, metrics, artifacts, index))
    first, second = logical[0], logical[1]
    require(first[3] == second[3] and first[1]["source"] == second[1]["source"]
            and first[1]["input_root"] == second[1]["input_root"] and first[1]["range_root"] == second[1]["range_root"],
            "full logical two-round scientific bytes/source/inputs")
    receipts, all_cases, signatures, audit_names = [], [], {}, set()
    for org in ORGANIZATIONS:
        shard_rounds = []
        for number in (1, 2):
            shard_name = f"svc-{prefix}-{org}-{number:02d}"
            shard = root / shard_name
            m, metrics, artifacts = checked_manifest(shard, dict(GRID, lane_profiles=[org]))
            index = metric_index(metrics, [org], suite)
            require(set(artifacts) == {"metrics.json"} | set(index), "shard all16 witnesses plus metrics")
            aggregate = logical[number - 1]
            require(m["source"] == aggregate[1]["source"] and m["input_root"] == aggregate[1]["input_root"]
                    and m["range_root"] == aggregate[1]["range_root"], "shard/logical actual service source and numeric inputs")
            aggregation = aggregate[1].get("aggregation_source", {})
            provenance = [r for r in aggregation.get("shards", []) if r["directory"] == shard_name]
            require(len(provenance) == 1 and provenance[0]["manifest"] == descriptor(shard / "manifest.json")
                    and provenance[0]["metrics"] == artifacts["metrics.json"] and provenance[0]["cases"] == 8
                    and provenance[0]["witnesses"] == 16, "logical aggregation original shard provenance")
            for name in index:
                require(index[name] == aggregate[4][name] and artifacts[name] == aggregate[3][name], "immutable shard/logical witness and metric mapping")
            shard_rounds.append((m, metrics, artifacts, index))
        require(shard_rounds[0][2] == shard_rounds[1][2], "original shard two-round byte identity")
        audit_path = root / f"receive-svc-{prefix}-{org}-01" / "audit.json"
        require(str(audit_path) not in audit_names, "distinct parallel audit receipts")
        audit_names.add(str(audit_path))
        audit = load(audit_path)
        cases = audit_cases(audit, shard_rounds[0][3], receiver_binding, receiver_binding_sha,
                            first[1]["input_root"], first[1]["range_root"])
        for case in cases:
            case = dict(case, parallel_shard=org, audit_sha256=sha(audit_path))
            all_cases.append(case)
        signatures[org] = audit.get("shared_split_signatures", [])
        receipts.append(dict(organization=org, audit=str(audit_path), audit_artifact=descriptor(audit_path),
            source=audit["source"], cases=16,
            shard01_manifest=descriptor(root / f"svc-{prefix}-{org}-01" / "manifest.json"),
            shard02_manifest=descriptor(root / f"svc-{prefix}-{org}-02" / "manifest.json")))
    names = [case["witness"] for case in all_cases]
    require(len(names) == len(set(names)) == 112 and set(names) == set(first[4]), "complete112 parallel independently audited witnesses")
    pairs = cross_label(signatures, suite, all_cases)
    finite = []
    for ext in GRID["ext_profiles"]:
        eligible = [case for case in all_cases if case["id"][4] == ext]
        winner = min(eligible, key=lambda c: (c["cycles"], c["witness"]))
        finite.append(dict(task=expected_task(suite), ext_ii=ext, candidates=len(eligible), winner=winner["witness"],
                           cycles=winner["cycles"], commit_contract=winner["commit_contract"],
                           scope="minimum in recorded finite grid; whole-pool shared8 is a different issue-granularity profile; no global optimum or physical merge claim"))
    result = dict(schema="issue68-parallel-service-audit/1", status="PASS_INDEPENDENT_SERVICE_SHARD_UNION", suite=suite,
        source=receipts[0]["source"],
        merge_source=dict(merge_audits_sha256=sha(__file__), commit=binding["commit"], binding=binding,
                          receiver_source_sha256=RECEIVER_SHA256, receiver_binding=descriptor(receiver_binding_path)),
        scientific_source=first[1]["source"], logical01_manifest=descriptor(first[0] / "manifest.json"),
        logical02_manifest=descriptor(second[0] / "manifest.json"), two_rounds=dict(all_scientific_SHA_identical=True, artifacts=113),
        parallel_audits=receipts, complete_witnesses=112, complete_best_case_rows=56,
        cases=all_cases, shared_split_label_only_pairs=48, shared_split_label_only_cycles_difference=0,
        shared_split_pairs=pairs, finite_groups=finite, seconds=time.monotonic() - begin,
        quality_accepted=False, hardware_implemented=False,
        replay_scope="Seven separately SHA-bound independent receiver jobs replayed16 witnesses each; this merge only checks bytes/source/coverage/metrics and48 cross-label signatures, and does not redo arithmetic/calendar/scheduling",
        limitation="Conditional declared cost and finite grid only; no RTL/PPA/full-model performance or application quality acceptance")
    save(out, result)
    print(json.dumps(dict(status=result["status"], witnesses=112, pairs=48)), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--suite", choices=("native", "legacy"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--binding", type=Path, required=True)
    p.add_argument("--receiver-binding", type=Path)
    args = p.parse_args()
    merge(args.root, args.suite, args.out, load(args.binding), args.receiver_binding)


if __name__ == "__main__":
    main()
