"""Solve a shard of Maxwell rows, each against all #206 conductors."""
import argparse
import json
import os
from pathlib import Path

from field_coupon import VALIDATION_SHA
from field_extract import measure
from run import save, sha


def solve(out, prep, accepted, shard, shards):
    geometry = json.loads((prep / "geometry.json").read_text())
    assert geometry["passed"] and geometry["net_count"] == 2491
    assert sha(prep / "field.in") == geometry["field_sha256"]
    approval = accepted / "result/validation.json"
    assert sha(approval) == VALIDATION_SHA
    binary = accepted / "field_row"
    assert sha(binary) == geometry["solver_sha256"]
    out.mkdir()
    model = out / "field.in"
    model.symlink_to((prep / "field.in").resolve(strict=True))
    ids = list(range(shard, geometry["net_count"], shards))
    rows = measure([(model, index) for index in ids], binary,
                   int(os.environ["SLURM_CPUS_PER_TASK"]), 1 << 18)
    assert [r["master"] for r in rows] == ids
    receipt = {str(i): sha(out / f"row-{i:03}.json") for i in ids}
    save(out / "shard.json", dict(passed=True, shard=shard, shards=shards,
         field_sha256=geometry["field_sha256"], solver_sha256=geometry["solver_sha256"],
         rows=receipt, walks=sum(r["walks"] for r in rows)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "prep", "accepted"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--shards", type=int, required=True)
    args = parser.parse_args()
    shard = int(os.environ["PEX_SHARD"])
    assert 0 <= shard < args.shards <= 2491
    solve(args.out, args.prep, args.accepted, shard, args.shards)
