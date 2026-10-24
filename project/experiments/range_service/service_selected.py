"""Collect/verify four original service witnesses with independent authority.

Offline verification covers schedule, capacity, transport and saved task/epoch
metadata. It does not recompute source NPZ arithmetic or prove RTL/PPA.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


SERVICE_SHA = "0fa2cc07aa192d746db34ebbb96ca512dcd52c99ff940c98ec0a98a85769d59c"
RECEIVER_SHA = "325a3668f6855019b43f273502e4ddb033e5f5422656c8bd070eaf777b492e75"
SCOPE = ("Four predeclared conditional S32D31 service witnesses only; independent offline schedule/calendar/"
         "capacity/transport and saved task unit/epoch checks. Original NPZ arithmetic and full source identity "
         "were accepted by the server receivers and separate R bundle, not recomputed here. Tile16/local "
         "old-new versus tile32/S4-shadow is a combined feasible configuration comparison, not isolated "
         "placement benefit; no RTL/PPA/full-model speed proof.")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def desc(p):
    p = Path(p)
    return {"bytes": p.stat().st_size, "sha256": sha(p)}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def safe(root, name):
    require(isinstance(name, str) and "\\" not in name and not Path(name).is_absolute() and
            name not in ("", ".") and ".." not in Path(name).parts, "unsafe package path")
    p = Path(root) / name
    require(p.resolve().is_relative_to(Path(root).resolve()), "package path escaped root")
    return p


def checked(root, name, wanted):
    p = safe(root, name)
    require(p.is_file() and desc(p) == {k: wanted[k] for k in ("bytes", "sha256")}, "artifact SHA/bytes mismatch: " + name)
    return p


def receiver_module(p):
    p = Path(p)
    require(sha(p) == RECEIVER_SHA, "frozen independent receiver SHA")
    spec = importlib.util.spec_from_file_location("issue68_selected_receiver", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authority(manifest, metrics, audit):
    require(manifest.get("schema") == "issue68-service/1" and
            manifest.get("source", {}).get("service_sha256") == SERVICE_SHA,
            "frozen producer source authority")
    require(metrics.get("source") == manifest["source"] and
            metrics.get("status") == "PASS_CONDITIONAL_SCHEDULE", "metrics source authority")
    require(str(audit.get("status", "")).startswith("PASS_INDEPENDENT_SERVICE") and
            audit.get("source", {}).get("receive_service_sha256") == RECEIVER_SHA,
            "original independent receiver authority")
    require(audit.get("complete_witnesses") == 112 and len(audit.get("cases", [])) == 112,
            "full independent112 witness authority")
    require(audit.get("quality_accepted") is False and audit.get("hardware_implemented") is False,
            "receiver scope cannot imply quality/hardware acceptance")
    require(len(manifest["artifacts"]) == 113 and len(metrics["results"]) == 56,
            "full aggregate SHA index and metrics authority")


def selected_case(manifest, metrics, audit, suite, tile):
    task = ("native.evaluation.S32.D31.guard_rescale" if suite == "native" else
            "legacy.layer0-end8192.S32.D31.guard_rescale")
    identity = [task, "shared4_4", tile, "reread", 1, "critical"]
    rows = [r for r in metrics["results"] if
            [r["task"], r["organization"], r["tile"], r["norm_route"], r["ext_ii"]] == identity[:5]]
    require(len(rows) == 1, "unique predeclared selected condition")
    r = rows[0]
    strategies = [s for s in r["strategies"] if s["strategy"] == "critical"]
    require(len(strategies) == 1, "selected critical strategy actually executed")
    s = strategies[0]
    cases = [a for a in audit["cases"] if a["id"] == identity and a["witness"] == s["witness"]]
    require(len(cases) == 1, "selected case missing original independent authority")
    a = cases[0]
    require(a["task_fingerprint"] == r["task_fingerprint"] and a["commit_contract"] == r["commit_contract"] and
            a["cycles"] == s["cycles"] and a["operations"] == s["nodes"] and
            a["resident_bytes"] == s["memory"] and a["payload_bytes"] == s["payload_bytes"] and
            a["wire_bytes"] == s["wire_bytes"] and a.get("physical_claim") is False,
            "selected metrics differ from independent receipt")
    require(s["witness"] in manifest["artifacts"], "selected artifact missing full SHA index")
    return r, s, a


def check_case(path, wanted, original_case, receiver):
    require(desc(path) == {k: wanted[k] for k in ("bytes", "sha256")}, "selected actual gzip SHA/bytes")
    w = json.loads(gzip.decompress(Path(path).read_bytes()))
    check = receiver.verify_witness(w)
    expected = {"cycles": check["makespan"], "independent_lower_bound": check["lower_bound"],
                "precedence_lower_bound": check["precedence_lower_bound"], "operations": check["operations"],
                "payload_bytes": check["payload_bytes"], "wire_bytes": check["wire_bytes"],
                "resident_bytes": check["resident_bytes"], "task_fingerprint": check["task_fingerprint"],
                "commit_contract": check["commit_contract"], "physical_claim": False}
    require(all(original_case.get(k) == v for k, v in expected.items()), "offline result differs from original independent case")
    require([w["task"]["id"], w["config"]["organization"], w["config"]["tile"],
             w["config"]["norm_route"], w["config"]["ext_ii"], w["config"]["strategy"]] == original_case["id"],
            "offline selected identity differs")
    return w, check


def collect(root, out, native_audit, legacy_audit, receiver, binding):
    root, out = Path(root).resolve(), Path(out).resolve()
    require(binding.get("service_selected_sha256") == sha(__file__) and binding.get("commit"), "selected source binding")
    require(not out.exists() and out.parent == root, "new selected output must remain in task root")
    require(sha(receiver) == RECEIVER_SHA, "frozen independent receiver source")
    planned, records, provenance = [], [], {}
    for suite, audit_path in (("native", Path(native_audit)), ("legacy", Path(legacy_audit))):
        source = root / ("service-" + suite + "01")
        manifest = load(source / "manifest.json")
        metrics = load(source / "metrics.json")
        checked(source, "metrics.json", manifest["artifacts"]["metrics.json"])
        audit = load(audit_path)
        authority(manifest, metrics, audit)
        for name, path in (("manifest.json", source / "manifest.json"),
                           ("metrics.json", source / "metrics.json"), ("audit.json", audit_path)):
            planned.append((path, suite + "/" + name, desc(path)))
        for tile in (16, 32):
            row, strategy, original = selected_case(manifest, metrics, audit, suite, tile)
            name = strategy["witness"]
            wanted = manifest["artifacts"][name]
            p = checked(source, name, wanted)
            w = json.loads(gzip.decompress(p.read_bytes()))
            require(w["task_fingerprint"] == original["task_fingerprint"] and
                    w["task"]["precision"]["state_bits"] == 32 and
                    w["task"]["precision"]["decay_fraction"] == 31,
                    "actual selected task precision/fingerprint")
            planned.append((p, suite + "/" + name, wanted))
            input_refs = {k: v for k, v in w["task"].items()
                          if k not in ("tokens", "precision", "commit_contract")}
            records.append({"suite": suite, "path": suite + "/" + name, "artifact": wanted,
                            "id": original["id"], "task_fingerprint": original["task_fingerprint"],
                            "precision": w["task"]["precision"], "commit_contract": original["commit_contract"],
                            "input_refs": input_refs, "original_case_sha256": hashlib.sha256(canonical(original)).hexdigest(),
                            "authority": {"manifest": suite + "/manifest.json", "metrics": suite + "/metrics.json", "audit": suite + "/audit.json"}})
        provenance[suite] = {"service_run": str(source), "independent_audit": str(audit_path),
                             "full_manifest": desc(source / "manifest.json"), "audit": desc(audit_path),
                             "producer_source": manifest["source"], "receiver_source": audit["source"]}
    planned.append((Path(receiver), "receive_service.py", desc(receiver)))
    out.mkdir()
    artifacts = {}
    for src, relative, wanted in planned:
        destination = safe(out, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, destination)
        require(desc(destination) == wanted, "copy verification")
        artifacts[relative] = wanted
    index = {"schema": "issue68-service-selected/1", "source": binding,
             "frozen_service_sha256": SERVICE_SHA, "frozen_receiver_sha256": RECEIVER_SHA,
             "cases": records, "artifacts": artifacts, "source_provenance": provenance,
             "scope": SCOPE, "numeric_quality_accepted": False, "hardware_implemented": False,
             "source_validation": "selected original gzip/metrics actually SHA checked; copied fullSHA indexes and original independent receipts bind selected case authority; unrelated full witness bytes not copied or revalidated here"}
    (out / "index.json").write_bytes(canonical(index))
    return {"status": "COLLECTED_FOUR_ORIGINAL_WITNESSES", "index": desc(out / "index.json"), "cases": 4,
            "scope": SCOPE}


def verify(index_path, out, receiver_path=None):
    index_path, out = Path(index_path).resolve(), Path(out).resolve()
    require(not out.exists(), "new offline receipt required")
    index, base = load(index_path), index_path.parent
    require(index.get("schema") == "issue68-service-selected/1" and
            index.get("frozen_service_sha256") == SERVICE_SHA and index.get("frozen_receiver_sha256") == RECEIVER_SHA,
            "selected package schema/source")
    require(index.get("numeric_quality_accepted") is False and index.get("hardware_implemented") is False,
            "selected scope cannot imply numeric/hardware acceptance")
    require(index.get("source", {}).get("service_selected_sha256") == sha(__file__), "selected verifier source SHA")
    for name, wanted in index["artifacts"].items():
        checked(base, name, wanted)
    receiver = receiver_module(receiver_path or (base / "receive_service.py"))
    require(len(index["cases"]) == 4 and
            {(c["suite"], c["id"][2]) for c in index["cases"]} == set((s, t) for s in ("native", "legacy") for t in (16, 32)),
            "exact predeclared four conditions")
    results = []
    for c in index["cases"]:
        refs = c["authority"]
        manifest, metrics, audit = [load(safe(base, refs[k])) for k in ("manifest", "metrics", "audit")]
        authority(manifest, metrics, audit)
        row, strategy, original = selected_case(manifest, metrics, audit, c["suite"], c["id"][2])
        require(c["id"] == original["id"] and c["path"] == c["suite"] + "/" + strategy["witness"] and
                c["task_fingerprint"] == original["task_fingerprint"], "selected index identity changed")
        require(c["artifact"] == manifest["artifacts"][strategy["witness"]] == index["artifacts"][c["path"]] and
                c["original_case_sha256"] == hashlib.sha256(canonical(original)).hexdigest(),
                "selected authority changed")
        w, check = check_case(safe(base, c["path"]), c["artifact"], original, receiver)
        require(c["precision"] == w["task"]["precision"] and c["commit_contract"] == original["commit_contract"],
                "selected format/contract metadata changed")
        require(c["input_refs"] == {k: v for k, v in w["task"].items()
                                   if k not in ("tokens", "precision", "commit_contract")},
                "selected source/input metadata changed")
        results.append({"path": c["path"], "artifact": c["artifact"], "status": check["status"],
                        "cycles": check["makespan"], "task_fingerprint": check["task_fingerprint"]})
    out.parent.mkdir(parents=True, exist_ok=True)
    negative_root = out.parent / (out.stem + "-negatives")
    require(not negative_root.exists(), "new negative directory required")
    negative_root.mkdir()
    first = next(c for c in index["cases"] if c["suite"] == "native" and c["id"][2] == 16)
    p = safe(base, first["path"])
    negative = receiver.actual_negative(p.parent, p.name, negative_root / "rehashed-epoch", "epoch")
    result = {"status": "PASS_OFFLINE_SELECTED_SERVICE_SCHEDULE", "source": {"service_selected_sha256": sha(__file__),
               "receive_service_sha256": RECEIVER_SHA}, "index": desc(index_path), "cases": results,
              "actual_rehashed_epoch_negative": negative, "scope": SCOPE,
              "original_NPZ_arithmetic_replayed": False, "numeric_quality_accepted": False, "hardware_implemented": False}
    out.write_bytes(canonical(result))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("collect")
    for name in ("root", "out", "legacy-audit", "receiver", "binding"):
        c.add_argument("--" + name, required=True)
    c.add_argument("--native-audit")
    v = sub.add_parser("verify")
    v.add_argument("--index", required=True)
    v.add_argument("--out", required=True)
    v.add_argument("--receiver")
    a = p.parse_args()
    if a.mode == "collect":
        root = Path(a.root)
        r = collect(root, a.out, a.native_audit or root / "receive-service-native01" / "audit.json",
                    a.legacy_audit, a.receiver, load(a.binding))
    else:
        r = verify(a.index, a.out, a.receiver)
    print(json.dumps({"status": r["status"], "cases": len(r["cases"]) if isinstance(r["cases"], list) else r["cases"]}))


if __name__ == "__main__":
    main()
