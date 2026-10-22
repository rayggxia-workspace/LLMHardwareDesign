"""Postprocessing: necessary single-net reachability, not a full routing oracle."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_dir", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit("Keep old diagnosis; choose a new output")
    workloads = json.loads((a.run_dir/"workloads.json").read_text(encoding="utf-8"))
    records, counts = [], defaultdict(lambda: defaultdict(int))
    for path in sorted(a.run_dir.glob("*-cases.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["status"] == "routed":
                continue
            base = json.loads((a.run_dir/"fabrics"/(row["variant"]+".json")).read_text(encoding="utf-8"))
            nets = defaultdict(set)
            for src, dst, port in workloads[row["workload"]]["edges"]:
                nets[row["mapping"][src]+".o"].add(row["mapping"][dst]+"."+port)
            # All pin components have one tap with capacity 1. An unrelated
            # input cannot serve as a two-connection passive transit junction.
            assert all(t["capacity"] == 1 for t in base["taps"].values()
                       if base["components"][t["component"]]["kind"] != "wire")
            no_path = []
            for driver, sinks in nets.items():
                blocked = {c for c, v in base["components"].items()
                           if (v["kind"] == "output" and c != driver)
                           or (v["kind"] == "input" and c not in sinks)}
                adj = defaultdict(set)
                for con in base["connectors"].values():
                    u, v = [base["taps"][con[k]]["component"] for k in ("a", "b")]
                    if u not in blocked and v not in blocked:
                        adj[u].add(v)
                        adj[v].add(u)
                seen, stack = set(), [driver]
                while stack:
                    u = stack.pop()
                    if u in seen:
                        continue
                    seen.add(u)
                    stack.extend(adj[u]-seen)
                no_path.extend({"driver": driver, "sink": s} for s in sorted(sinks-seen))
            kind = "single_net_unreachable_for_this_mapping" if no_path else "single_net_reachable_full_routing_unknown"
            counts[row["variant"]+":"+row["method"]][kind] += 1
            records.append({"variant": row["variant"], "method": row["method"],
                            "workload": row["workload"], "seed": row["seed"],
                            "diagnosis": kind, "unreachable_pairs": no_path})
    manifest_bytes = (a.run_dir/"manifest.json").read_bytes()
    result = {"source_commit": json.loads(manifest_bytes)["source_commit"],
              "input_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "postprocessor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Ignore capacity/other nets; no path proves only fixed-mapping model unreachability. Reachable is not a full feasibility proof.",
              "counts": dict(counts), "failed_rows": records}
    a.out.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(dict(counts), indent=2))


if __name__ == "__main__":
    main()
