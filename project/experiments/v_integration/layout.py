"""Issue91 address/lifetime trace generator; no tensor values or RTL timing model."""
import argparse
import gzip
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCES = ["project/rtl/wide_service/wide_block.sv", "project/rtl/wide_service/wide_engine.sv",
           "project/rtl/wide_service/ram128.sv", "project/rtl/wide_service/byte_alu.sv",
           "project/rtl/norm_service/store82.sv", "project/rtl/runtime_cache/chain85.sv",
           "project/rtl/runtime_cache/mfront85.sv", "project/rtl/runtime_cache/norm84.sv",
           "project/rtl/runtime_cache/mul84.sv", "project/rtl/runtime_cache/sfu84.sv",
           "project/experiments/block_circuit/assemble.py",
           "project/experiments/block_circuit/results/issue-80/comparison.json",
           "project/experiments/granite_ports/run_server.py",
           "project/experiments/moe_grouped/granite_chain.py"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def integer(value, name):
    if type(value) is not int:
        raise ValueError("integer required: " + name)
    return value


def check_layout(profile, capacity=16384, line=16):
    errors = []
    rows = profile["regions"]
    if len({r["name"] for r in rows}) != len(rows):
        errors.append("duplicate region name")
    for r in rows:
        start, size = integer(r["start"], "start"), integer(r["bytes"], "bytes")
        if start < 0 or size <= 0 or start + size > capacity:
            errors.append("out of bounds: " + r["name"])
        if start % line or size % line:
            errors.append("alignment: " + r["name"])
        if not r["live"] or len(r["live"]) != len(set(r["live"])):
            errors.append("invalid lifetime: " + r["name"])
    for i, a in enumerate(rows):
        for b in rows[i+1:]:
            if set(a["live"]) & set(b["live"]) and max(a["start"], b["start"]) < min(a["start"]+a["bytes"], b["start"]+b["bytes"]):
                errors.append("live overlap: " + a["name"] + "/" + b["name"])
    by_phase = {phase: sum(r["bytes"] for r in rows if phase in r["live"])
                for phase in sorted({phase for r in rows for phase in r["live"]})}
    return {"valid": not errors, "errors": errors, "active_bytes_by_phase": by_phase}


def events(profile, contract):
    """Each memory event is [bus, R/W, byte address, X/G/Y, logical line, phase]."""
    h, tile = profile["h"], profile["tile"]
    if not check_layout(profile)["valid"] or h % 4 or tile % 4 or not 4 <= h <= 2560:
        raise ValueError("unsupported profile")
    regions = {r["name"]: r for r in profile["regions"]}
    xy, gamma = regions["XY"]["start"], regions["G"]["start"]
    n, t = h // 4, tile // 4
    ext = contract["structural_input_addresses"]
    if regions["XY"]["bytes"] < (h if profile["mode"] == "resident" else tile)*4 or regions["G"]["bytes"] < tile*4:
        raise ValueError("insufficient tile region")
    def load(obj, logical, physical, phase):
        yield ["E", "R", ext[obj]+16*logical, obj, logical, phase]
        yield ["S", "W", physical, obj, logical, phase]
    if profile["mode"] == "resident":
        for i in range(n):
            yield from load("X", i, xy+16*i, "load_x")
        for i in range(n):
            yield ["S", "R", xy+16*i, "X", i, "stats"]
    else:
        for first in range(0, n, t):
            for i in range(first, min(first+t, n)):
                yield from load("X", i, xy+16*(i-first), "load_stats_x")
            for i in range(first, min(first+t, n)):
                yield ["S", "R", xy+16*(i-first), "X", i, "stats"]
    yield ["C", "DEN", h]
    for first in range(0, n, t):
        last = min(first+t, n)
        if profile["mode"] == "stream":
            for i in range(first, last):
                yield from load("X", i, xy+16*(i-first), "load_output_x")
        for i in range(first, last):
            yield from load("G", i, gamma+16*(i-first), "load_gamma")
        for i in range(first, last):
            addr = xy+16*(i if profile["mode"] == "resident" else i-first)
            yield ["S", "R", addr, "X", i, "output"]
            yield ["S", "R", gamma+16*(i-first), "G", i, "output"]
            yield ["C", "NORM", i]
            yield ["S", "W", addr, "Y", i, "output"]
            yield ["S", "R", addr, "Y", i, "egress"]
            yield ["E", "W", ext["Y"]+16*i, "Y", i, "egress"]
        yield ["C", "GAMMA_RELEASE", first, last-first]
    yield ["C", "DONE", h]


def counters(trace, contract):
    c = Counter()
    for e in trace:
        if e[0] in ("E", "S"):
            c[e[0]+"_"+e[1]] += 1
    c["external_transactions"] = c["E_R"] + c["E_W"]
    c["external_payload_bytes"] = c["external_transactions"]*16
    c["prototype_wire_bytes"] = c["external_transactions"]*contract["external_transaction_beats"]*contract["external_beat_bytes"]
    c["store_operations"] = c["S_R"]+c["S_W"]
    c["store_line_bytes"] = c["store_operations"]*16
    return dict(c)


def run(out, contract_path=HERE / "contract.json"):
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if out.exists():
        raise ValueError("output must be new")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    own = [str(p.relative_to(ROOT)).replace("\\", "/") for p in HERE.iterdir() if p.suffix in (".py", ".json")]
    bound = []
    for name in sorted(set(SOURCES+own)):
        raw = subprocess.check_output(["git", "show", commit+":"+name], cwd=ROOT)
        if raw != (ROOT/name).read_bytes():
            raise ValueError("uncommitted input/source: "+name)
        bound.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    out.mkdir(parents=True)
    report = {"schema": "v-integration91-structure-v1", "status": "STRUCTURAL_ONLY_NOT_RTL",
              "source_commit": commit, "contract_sha256": sha(contract_path), "sources": bound,
              "layouts": {}, "traces": {}, "exclusions": contract["notes"]}
    for p in contract["profiles"]:
        layout = check_layout(p)
        if layout["valid"] != p["expect_valid"]:
            raise ValueError("unexpected layout: "+p["id"])
        report["layouts"][p["id"]] = layout
        if "mode" not in p:
            continue
        trace = list(events(p, contract))
        data = "".join(json.dumps(e, separators=(",", ":"))+"\n" for e in trace).encode("ascii")
        path = out/(p["id"]+".jsonl.gz")
        path.write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
        report["traces"][p["id"]] = {"path": path.name, "bytes": path.stat().st_size,
                                   "sha256": sha(path), "events": len(trace), "counters": counters(trace, contract)}
    write_json(out/"report.json", report)
    print(json.dumps({"status": report["status"], "profiles": len(report["layouts"]), "traces": len(report["traces"]), "report_sha256": sha(out/"report.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.out)
