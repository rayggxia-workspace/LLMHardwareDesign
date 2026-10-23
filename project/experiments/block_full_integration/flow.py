#!/usr/bin/env python3
"""Entry point for the developing full-hardware integration flow.

Adapters report their precise scope. A successful inventory is not a successful
integration or routing stage. Unimplemented stages fail explicitly.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def invoke(filename, argv):
    adapter = HERE / filename
    if not adapter.is_file():
        raise RuntimeError("Adapter is not implemented yet: " + filename)
    return subprocess.call([sys.executable, "-B", "-I", "-S", str(adapter), *argv])

def replay(receipt, output):
    """Re-execute the original native inventory with pinned source and inputs.

    This deliberately uses the archived adapter, not the newest working code.
    Other experiment types need their own evidence-preserving replay adapter.
    """
    if not (os.getenv("SLURM_JOB_ID") or os.getenv("TASK_JOB_ID")):
        raise RuntimeError("Replay requires a scheduler allocation")
    r = json.loads(Path(receipt).read_text(encoding="utf-8"))
    if r.get("status") != "pass_inventory_only":
        raise RuntimeError("Replay currently accepts successful native inventory receipts only")
    records = list(r["inputs"].values()) + [r["config"]]
    records += [r["tools"]["adapter"], r["tools"]["native_script"], r["tools"]["openroad"]]
    for item in records:
        if item.get("exists") and sha256(item["path"]) != item["sha256"]:
            raise RuntimeError("Input or tool changed; previous evidence is invalid: " + item["path"])
    return subprocess.call([
        sys.executable, "-B", "-I", "-S", r["tools"]["adapter"]["path"], "run",
        "--config", r["config"]["path"], "--case", r["case"]["id"],
        "--output", output,
    ])

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    inventory = sub.add_parser("inventory", help="Native physical or source/coverage inventory")
    inventory.add_argument("--adapter", choices=("native", "rtl"), required=True)
    inventory.add_argument("adapter_args", nargs=argparse.REMAINDER)
    integrate = sub.add_parser("integrate", help="Whole-RTL hierarchy/partition adapter")
    integrate.add_argument("adapter_args", nargs=argparse.REMAINDER)
    for name in ("prepare-base", "route"):
        q = sub.add_parser(name, help="Requires implemented and qualified stage adapter")
        q.add_argument("adapter_args", nargs=argparse.REMAINDER)
    verify = sub.add_parser("verify", help="Independent inventory audit; scope follows selected adapter")
    verify.add_argument("--adapter", choices=("native",), required=True)
    verify.add_argument("adapter_args", nargs=argparse.REMAINDER)
    q = sub.add_parser("replay", help="Pinned native inventory replay into a new directory")
    q.add_argument("--receipt", required=True)
    q.add_argument("--output", required=True)
    args = p.parse_args()
    extra = getattr(args, "adapter_args", [])
    if extra and extra[0] == "--":
        extra = extra[1:]
    if args.command == "inventory":
        return invoke({"native":"native_inventory.py", "rtl":"rtl_inventory.py"}[args.adapter], extra)
    if args.command == "integrate":
        return invoke("partition.py", extra)
    if args.command == "verify":
        return invoke("native_review.py", extra)
    if args.command == "replay":
        return replay(args.receipt, args.output)
    return invoke({"prepare-base":"prepare_base.py", "route":"route.py"}[args.command], extra)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(json.dumps({"execution_status":"blocked_or_invalid_input", "reason":str(exc)}), file=sys.stderr)
        sys.exit(2)
