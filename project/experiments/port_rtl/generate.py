"""Build fixed-shape Issue27 traffic programs; arithmetic remains synthetic.

The emitted programs carry per-object write generations. Reads must return the
intended generation, in addition to the simulator's memory scoreboard checks.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import itertools
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("state_graph", HERE.parent / "state_ports/graph.py")
graph_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_module)

def emit_case(path, graph, policy, stalls, mode, depth, mask):
    tasks = graph["tasks"]
    ids = {t["id"]: i for i, t in enumerate(tasks)}
    access = {a["id"]: a for a in graph["accesses"]}
    last, rows = {}, []
    for i, t in enumerate(tasks):
        dep = [ids[d] for d in t["deps"]]
        if t["kind"] == "compute":
            fields = [i, 0, "MVD".index(t["engine"]), 0, 0, 0, 0, t["duration"], -1]
        else:
            a = access[t["id"]]
            version = last.get(a["object"], -1)
            if a["direction"] == "W":
                last[a["object"]] = i
            elif version < 0:
                raise ValueError("read before generation initialization")
            fields = [i, 1, "MVD".index(a["engine"]), a["bank"], int(a["direction"] == "W"),
                      a["offset"], a["bytes"], 2, version]
        rows.append(" ".join(map(str, fields + [len(dep)] + dep)))
    # Scheduling priority is recomputed from the same fixed Issue27 service DAG.
    succ = [[] for _ in tasks]
    for i, t in enumerate(tasks):
        for d in t["deps"]:
            succ[ids[d]].append(i)
    memo = {}
    def rank(i):
        if i not in memo:
            memo[i] = tasks[i]["duration"] + max((rank(j) for j in succ[i]), default=0)
        return memo[i]
    priorities = [rank(i) if policy == "critical" else
                  (-t["duration"] if policy == "shortest" else t["duration"] if policy == "longest" else 0)
                  for i, t in enumerate(tasks)]
    path.write_text(f"{len(tasks)} {stalls} {mode} {depth} {mask}\n" + " ".join(map(str, priorities)) + "\n" +
                    "\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return {"task_ids": [t["id"] for t in tasks], "traffic": graph["traffic"],
            "bank_reserved_bytes": graph["bank_reserved_bytes"],
            "scratch_reserved_bytes": graph["scratch_reserved_bytes"],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    evidence = HERE.parent / "state_ports/results/issue-27-run01/evidence.zip"
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    if evidence_sha != "f760dec66344c11fe9c7f04f55d91f610157d7ad624f6d66faa6a9bbdb1f1588":
        raise ValueError("Issue27 evidence archive mismatch")
    with zipfile.ZipFile(evidence) as z:
        binding_bytes = z.read("run/trace-binding.json")
    observed = json.loads(binding_bytes)["observations"]
    if [o["shape"] for o in observed] != [[1,16,32,128],[1,8,32,128],[1,16,1,128],[1,8,48,128]]:
        raise ValueError("unexpected actual trace shapes")
    args.output.mkdir(parents=True, exist_ok=False)
    cases, rejected = [], []
    config = dict(key_tile=16, max_query_tile=32, bank_port_bytes_per_cycle=64,
                  link_bytes_per_cycle=64, external_bytes_per_cycle=32,
                  matrix_macs_per_cycle=1024, vector_elements_per_cycle=16,
                  endpoint_staging_bytes=64, burst_setup_cycles=2,
                  bank_bytes=[65536,65536], scratch_bytes={"M":65536,"V":65536})
    combinations = itertools.product(range(3), (1,2,4), ("prefill32", "decode48"),
                                     itertools.product((0,1), repeat=3),
                                     ("critical","fifo","shortest","longest"), (0,1), (63,59,31))
    for mode, depth, phase, placement_bits, policy, stalls, mask in combinations:
        place = dict(zip(("O","m","l"), placement_bits))
        config["bank_ports"] = ("1RW","1R1W","2RW")[mode]
        workload = dict(queries=32 if phase=="prefill32" else 1,
                        keys=32 if phase=="prefill32" else 48, head_dim=128)
        disabled = [f"{e}{b}" for ep,e in enumerate("MVD") for b in (0,1) if not (mask & (1 << (ep*2+b)))]
        meta = dict(mode=mode, depth=depth, phase=phase, placement=place, policy=policy,
                    stalls=stalls, mask=mask, disabled=disabled)
        name = f"m{mode}-d{depth}-{phase}-p{''.join(map(str,placement_bits))}-{policy}-s{stalls}-l{mask}"
        try:
            graph = graph_module.make_graph(config, workload, place, disabled)
        except graph_module.Infeasible as exc:
            rejected.append(dict(name=name, **meta, reason=str(exc)))
            continue
        binding = emit_case(args.output / (name+".case"), graph, policy, stalls, mode, depth, mask)
        cases.append(dict(name=name, **meta, **binding))
    result = dict(schema=1, source_graph="Issue27@6ffb9417 / graph.py unchanged in PR28",
                  shape_evidence="Issue27 actual layer0/head0 prefill32/decode48; synthetic data/service",
                  evidence_archive_sha256=evidence_sha,
                  trace_binding_sha256=hashlib.sha256(binding_bytes).hexdigest(),
                  graph_sha256=hashlib.sha256((HERE.parent/"state_ports/graph.py").read_bytes()).hexdigest(),
                  config={k:v for k,v in config.items() if k != "bank_ports"}, cases=cases, rejected=rejected)
    (args.output/"index.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"cases":len(cases),"rejected":len(rejected)}))

if __name__ == "__main__":
    main()
