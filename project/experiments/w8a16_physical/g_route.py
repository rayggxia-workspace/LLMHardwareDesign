"""Route explicitly qualified leaf mappings using the native M1-M10 engine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from native import check as check_native

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"project/experiments/block_v2"))
from physical import implement
import pins
from g_pins import generate as edge_pins


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", choices=("g_s32", "e_s32_ap64"), default="g_s32")
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--side", type=int, required=True)
    parser.add_argument("--bands", type=int, choices=[2, 3, 4], default=2)
    parser.add_argument("--margin", type=int, default=14)
    parser.add_argument("--density", type=float, required=True)
    parser.add_argument("--upper-adjustment", type=float)
    parser.add_argument("--pin-profile", choices=["legacy", "edge"], default="edge")
    parsed = parser.parse_args()
    cpus = len(os.sched_getaffinity(0))
    assert cpus in {10, 12} and parsed.side > 2*parsed.margin
    check_native()
    assert 0 < parsed.density <= 1
    if parsed.pin_profile == "edge":
        # The unchanged generic engine imports this explicit layout callback.
        # It retains the same planner API and independent complete rule checks.
        pins.generate = edge_pins
    parsed.out.mkdir(parents=True, exist_ok=False)
    args = argparse.Namespace(top=parsed.top, mapping=parsed.mapping, out=parsed.out,
        side=parsed.side, pin_bands=parsed.bands, core_margin=parsed.margin, density=parsed.density,
        cpus=cpus, grow_to_fit=False, upper_adjustment=parsed.upper_adjustment,
        r_compact_floorplan=False, r_strong_clock=False, remove_abc_buffers=False,
        placement_mode="timing", fanout_mode="original", refine_partition_placement=False,
        placement_hold_margin=None, input_receivers=True, hold_repair_margin=.02)
    inputs = {}
    for folder in ["project/experiments/block_v1", "project/experiments/block_feed_v1",
                   "project/experiments/block_v2", "project/experiments/w8a16_physical", "project/rtl/w8a16_v1"]:
        for path in (ROOT/folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                inputs[path.relative_to(ROOT).as_posix()] = sha(path)
    receipt = dict(passed=False, top=args.top, affinity=sorted(os.sched_getaffinity(0)),
                   start_unix=time.time(), inputs=inputs, commands=[],
                   pin_profile=parsed.pin_profile,
                   scope="Generic main physical implementation reused by explicit new top; completion is not acceptance")
    def run(command, log):
        command = list(map(str, command))
        start = time.time()
        with (args.out/log).open("w") as stream:
            proc = subprocess.run(command, cwd=args.out, stdout=stream, stderr=subprocess.STDOUT)
        receipt["commands"].append(dict(command=command, log=log, sha256=sha(args.out/log),
                                         returncode=proc.returncode, seconds=time.time()-start))
        assert proc.returncode == 0, (log, proc.returncode)
    try:
        implement(args, run)
        receipt["passed"] = True
    finally:
        receipt["end_unix"] = time.time()
        receipt["outputs"] = {path.relative_to(args.out).as_posix(): sha(path)
                              for path in args.out.rglob("*") if path.is_file()}
        (args.out/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    main()
