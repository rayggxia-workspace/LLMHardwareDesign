"""Compare reviewed P block port declarations without qualifying a product top."""

import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def checked_bytes(path, pin):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != pin["sha256"]:
        raise ValueError(f"SHA-256 mismatch for {path.name}")
    blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    if hashlib.sha1(blob).hexdigest() != pin["git_blob"]:
        raise ValueError(f"Git blob mismatch for {path.name}")
    return data.decode("utf-8")


def ports(text, module):
    header = text.split(f"module {module} (", 1)[1].split(");", 1)[0]
    result = {}
    for part in header.split(","):
        part = part.strip()
        decl = re.match(r"(input|output)\s+(?:wire|reg)\s+(\[[^\]]+\])?\s*(\w+)$", part)
        if decl:
            direction, width, name = decl.groups()
        else:
            name = part
        if not re.fullmatch(r"\w+", name) or name in result:
            raise ValueError(f"Invalid or duplicate port declaration: {part}")
        result[name] = (direction, width or "1")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="pu_p_group.sv from the pinned PR #214 commit")
    parser.add_argument("--require-production", action="store_true")
    args = parser.parse_args()
    review = json.loads((HERE / "a1_endpoint_review.json").read_text(encoding="utf-8"))
    try:
        old = review["block_p16"]
        base = ports(checked_bytes(ROOT / old["path"], old), "block_p16")
        candidate = ports(checked_bytes(args.candidate, review["p_group_candidate"]), "pu_p_group")
        if base != candidate:
            mismatches = sorted(name for name in base.keys() | candidate.keys()
                                if base.get(name) != candidate.get(name))
            raise ValueError("Block boundary differs: " + ", ".join(mismatches))
        pending = [name for name, entry in review["production"].items() if entry["binding"] is None]
        if len(pending) != len(review["production"]):
            raise ValueError("A product binding needs its own integration review")
    except (ValueError, OSError, KeyError, IndexError) as exc:
        parser.exit(1, f"invalid A1 review: {exc}\n")
    print(json.dumps({"matched_ports": len(base), "production_ready": False, "pending": pending}))
    return 2 if args.require_production else 0


if __name__ == "__main__":
    raise SystemExit(main())
