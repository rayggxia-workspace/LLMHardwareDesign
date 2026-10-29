"""Inspect real elaborated memories, arithmetic and pins, optionally map cells.

No physical/STA/DRC/LEC claim is made by this source/synthesis check.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
RTL = ROOT / "project/rtl/block_feed_v1"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def number(x):
    return int(x, 2) if isinstance(x, str) else x


def inspect(top, args):
    out = args.out / top
    out.mkdir(exist_ok=False)
    names = ["block_feed_m"] if top == "block_feed_m" else ["block_feed_s_macro", "block_feed_loader", "block_feed_s16k"]
    sources = [RTL / (n + ".sv") for n in names]
    script = "read_verilog -sv " + " ".join(map(str, sources)) + "\n"
    script += f"hierarchy -check -top {top}\nproc\nflatten\nopt\nmemory_collect\ncheck -assert\nstat\nwrite_json structure.json\n"
    if args.liberty:
        script += "synth -top " + top + " -noabc\n"
        script += "dfflibmap -liberty " + str(args.liberty) + "\n"
        script += "abc -exe " + str(args.abc) + " -liberty " + str(args.liberty) + "\n"
        script += "clean\ncheck -assert\nstat -liberty " + str(args.liberty) + "\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n"
    (out / "inspect.ys").write_text(script)
    with (out / "yosys.log").open("w") as stream:
        proc = subprocess.run([args.yosys, "-s", "inspect.ys"], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
    if proc.returncode:
        raise RuntimeError(f"{top}: Yosys exited {proc.returncode}; see {out / 'yosys.log'}")
    mod = json.loads((out / "structure.json").read_text())["modules"][top]
    memories, muls = {}, Counter()
    for name, cell in mod["cells"].items():
        p = cell["parameters"]
        if cell["type"].startswith("$mem"):
            memories[name] = {k: number(p[k]) for k in ("WIDTH", "SIZE", "RD_PORTS", "WR_PORTS")}
        if cell["type"] == "$mul":
            muls[f"{number(p['A_WIDTH'])}x{number(p['B_WIDTH'])}"] += 1
    if top == "block_feed_m" and muls["8x8"] != 64:
        raise RuntimeError(f"unexpected S8 multiplier count: {muls}")
    result = dict(passed=True, top=top, source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
                  ports={n: dict(direction=p["direction"], bits=len(p["bits"])) for n, p in mod["ports"].items()},
                  signal_pin_bits=sum(len(p["bits"]) for p in mod["ports"].values()),
                  memories=memories, multipliers=dict(muls), physical_qualified=False)
    if args.liberty:
        mapped = json.loads((out / "mapped.json").read_text())["modules"][top]
        counts = Counter(c["type"] for c in mapped["cells"].values())
        if any(n.startswith("$") for n in counts):
            raise RuntimeError(f"unmapped cells: {counts}")
        result.update(mapped=True, cell_counts=dict(counts), cell_count=sum(counts.values()),
                      liberty_sha256=sha(args.liberty), mapped_verilog_sha256=sha(out / "mapped.v"))
    (out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--yosys", default="yosys")
    p.add_argument("--liberty", type=Path)
    p.add_argument("--abc", default="yosys-abc")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [pool.submit(inspect, n, args) for n in ("block_feed_m", "block_feed_s_macro")]
        for f in as_completed(tasks):
            try:
                r = f.result();results.append(r);print("PASS", r["top"], flush=True)
            except Exception as exc:
                errors.append(str(exc));print("FAIL", exc, flush=True)
    result = dict(passed=not errors, results=results, errors=errors,
                  yosys=subprocess.check_output([args.yosys, "-V"], text=True).strip(),
                  physical_qualified=False)
    (args.out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
