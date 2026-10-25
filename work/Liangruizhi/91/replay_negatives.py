"""Replay the four Issue91 delivery mutations in a new task directory."""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "project/experiments/v_integration"))
import verify

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    results = []
    def check(name, change):
        d = a.out/name
        d.mkdir()
        for src in a.source.iterdir():
            if src.is_file():
                (d/src.name).write_bytes(src.read_bytes())
        report = json.loads((d/"report.json").read_text(encoding="utf-8"))
        change(d, report)
        (d/"report.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        try:
            verify.verify(d)
        except ValueError as exc:
            results.append({"case": name, "status": "REJECTED", "error": str(exc)})
        else:
            raise AssertionError("accepted mutation: "+name)
    def gamma(d, report):
        item = report["traces"]["h2560_stream_gamma"]
        path = d/item["path"]
        trace = [json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines()]
        trace.pop(next(i for i,e in enumerate(trace) if e[:2] == ["C", "GAMMA_RELEASE"]))
        path.write_bytes(gzip.compress("".join(json.dumps(e, separators=(",", ":"))+"\n" for e in trace).encode(), mtime=0))
        item.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), events=len(trace))
    check("negative-resigned-gamma", gamma)
    check("negative-reported-counters", lambda d,r: r["traces"]["h2560_stream_gamma"]["counters"].update(E_R=True))
    check("negative-source-hash", lambda d,r: r["sources"][0].update(sha256="0"*64))
    check("negative-unknown-schema", lambda d,r: r.update(extra_claim="RTL_PASS"))
    receipt = {"schema": "v-integration91-negative-receipt-v1", "status": "PASS_ALL_REJECTED", "cases": results}
    (a.out/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt))
if __name__ == "__main__":
    main()
