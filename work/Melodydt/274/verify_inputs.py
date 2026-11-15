"""Verify archived checkpoint and compiler graph inputs for #274."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


GRAPHS = {
    "qwen3": ("full-qwen3", "qwen3"),
    "qwen35": ("qwen35_global", "qwen35_linear"),
    "gemma": ("gemma_global", "gemma_local"),
    "phi": ("phi",),
    "granite": ("granite",),
    "falcon": ("falcon",),
}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inspect(suite, graph_root, name):
    frozen = json.loads(suite.read_text())["models"][name]
    checkpoint = Path(frozen["checkpoint"])
    inputs = {}
    for filename, expected in frozen["checkpoint_inputs"].items():
        path = checkpoint / filename
        actual = {"bytes": path.stat().st_size, "sha256": digest(path)}
        if actual != expected:
            raise ValueError("archive mismatch for {}: {}".format(path, actual))
        inputs[filename] = actual
    meta = dict(line.split(maxsplit=1) for line in
                (checkpoint / "metadata.txt").read_text().splitlines() if line.strip())
    graphs = {}
    for graph_name in GRAPHS[name]:
        path = graph_root / (graph_name + ".graph.json")
        graph = json.loads(path.read_text())
        graphs[graph_name] = {
            "path": str(path), "sha256": digest(path),
            "source": graph["source"], "source_sha256": graph["source_sha256"],
            "operations": dict(Counter(task["op"] for task in graph["tasks"])),
            "inputs": graph["inputs"], "outputs": graph["outputs"],
        }
    return {
        "model": name, "checkpoint": str(checkpoint), "inputs": inputs,
        "family": meta["family"],
        "geometry": {key: int(meta[key]) for key in
                     ("hidden", "intermediate", "layers", "heads",
                      "kv_heads", "head_dim", "vocab")},
        "graphs": graphs, "historical_reference_gate_passed": frozen["passed"],
        "scope": "checkpoint integrity and compiler graph inventory",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("suite", type=Path)
    p.add_argument("graphs", type=Path)
    p.add_argument("model", choices=sorted(GRAPHS))
    p.add_argument("output", type=Path)
    args = p.parse_args()
    receipt = inspect(args.suite, args.graphs, args.model)
    with args.output.open("x") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write("\n")
    print("{}: {} checkpoint files verified, {} graphs indexed".format(
        args.model, len(receipt["inputs"]), len(receipt["graphs"])))


if __name__ == "__main__":
    main()
