"""Inventory and snapshot the exact native inputs used by PR206, without P&R."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil

KINDS = ("C0", "F0", "J0", "P0", "T0", "U0")
RECEIPT = Path("/public/home/yuzelu/PingyangHuang/issue-215-top-pex-zOz2uxIr/route-206.json")
RECEIPT_SHA = "2c828b457b1351a52bfa2c516127ef138a59dc53f56557d285f20a3a040b25f7"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--index", type=int, required=True, choices=range(6))
    args = parser.parse_args()
    assert sha(RECEIPT) == RECEIPT_SHA
    receipt = json.loads(RECEIPT.read_text())
    kind = KINDS[args.index]
    reference = receipt["native_masks"][kind]
    gds = Path(reference["path"])
    assert gds.stat().st_size == reference["bytes"] and sha(gds) == reference["sha256"]
    sources = {suffix: gds.with_suffix("." + suffix) for suffix in ("gds", "odb", "v", "sdc", "spef")}
    source_hashes = {name: {"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)} for name, p in sources.items()}
    out = args.out.resolve()
    out.mkdir()
    here = Path(__file__).resolve().parent
    env = dict(os.environ, COUPLING_NATIVE_ODB=str(sources["odb"]),
               COUPLING_NATIVE_OUT=str(out),
               COUPLING_GEOMETRY_TCL=str(here.parent / "block_v1/odb_geometry.tcl"))
    with (out / "openroad.log").open("xb") as log:
        subprocess.run(["openroad", "-no_init", "-exit", str(here / "native_snapshot.tcl")],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    raw = out / "conductors.tsv"
    compressed = out / "conductors.tsv.gz"
    with raw.open("rb") as source, compressed.open("xb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0, compresslevel=3) as zipped:
            shutil.copyfileobj(source, zipped)
    # This is a temporary file created by this invocation, never a source input.
    raw_sha, raw_bytes = sha(raw), raw.stat().st_size
    raw.unlink()
    outputs = {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)} for p in out.iterdir() if p.is_file()}
    report = dict(kind=kind, source_receipt_sha256=RECEIPT_SHA,
                  source_hashes=source_hashes, outputs=outputs,
                  geometry_uncompressed_sha256=raw_sha, geometry_uncompressed_bytes=raw_bytes,
                  scope="Actual routed wires, special wires and pin geometry. Macro OBS excluded. Nested masters require explicit follow-up; not a complete flattened transistor layout.")
    # Verify original native inputs have not changed during readback.
    assert all(sha(sources[name]) == entry["sha256"] for name, entry in source_hashes.items())
    (out / "snapshot.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
