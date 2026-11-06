"""Join corrected geometry evidence to a fully completed, immutable physical audit."""
import argparse
import hashlib
import json
from pathlib import Path

GATES = {"physical", "abstract_lef", "timing", "native_drc", "stream_drc",
         "stream_geometry", "equivalence"}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    for name in ("producer", "original", "geometry", "out"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    producer = args.producer.resolve() / "completion.json"
    old, new = (d.resolve() / "receipt.json" for d in (args.original, args.geometry))
    a, b = (json.loads(p.read_text()) for p in (old, new))
    assert a["passed"] is False and b["passed"] is False
    assert a["input_receipt_sha256"] == b["input_receipt_sha256"] == sha(producer)
    assert a["approved_sdc_sha256"] == b["approved_sdc_sha256"]
    assert set(a["checks"]) == GATES and a["checks"]["stream_geometry"]["passed"] is False
    assert all(a["checks"][key]["passed"] is True for key in GATES - {"stream_geometry"})
    assert set(b["checks"]) == {"stream_geometry"} and b["scope"] == "diagnostic geometry-only"
    assert b["checks"]["stream_geometry"]["passed"] is True
    done = json.loads(producer.read_text())["outputs"]
    assert all(sha(p) == expected for p, expected in done.items())
    geometry_file = new.parent / "stream-geometry.json"
    proof = json.loads(geometry_file.read_text())
    assert proof["passed"] and all(proof["inputs"][p] == h for p, h in done.items()
                                   if Path(p).suffix in (".gds", ".odb", ".def"))
    assert all(b["checks"]["stream_geometry"][k] == v for k, v in proof.items())
    a["checks"]["stream_geometry"] = b["checks"]["stream_geometry"]
    a["geometry_supersession"] = {
        "original_audit": str(old), "original_audit_sha256": sha(old),
        "geometry_audit": str(new), "geometry_audit_sha256": sha(new),
        "geometry_file_sha256": sha(geometry_file),
        "reason": "Producer used normalized bank GDS; original bank GDS is the input to independent mask comparison.",
    }
    a["passed"] = True
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for path in old.parent.iterdir():
        if path.name not in ("receipt.json", "stream-geometry.json") and path.is_file():
            (out / path.name).symlink_to(path)
    (out / "stream-geometry.json").symlink_to(geometry_file)
    (out / "receipt.json").write_text(json.dumps(a, indent=2) + "\n")


if __name__ == "__main__":
    main()
