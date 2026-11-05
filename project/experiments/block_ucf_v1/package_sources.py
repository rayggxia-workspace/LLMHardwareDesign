"""Archive exact RTL, physical scripts, bank inputs and CTS checkpoints for a passed delivery."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign")
SOURCE_SUFFIX = {".gds", ".guide", ".json", ".lef", ".lib", ".lyt", ".mk", ".py", ".rpt",
                 ".sdc", ".sh", ".sv", ".svh", ".tcl", ".tsv", ".v", ".vlt"}


def sha(path):
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
        return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("delivery", type=Path)
    parser.add_argument("--candidate", action="append", nargs=3, required=True,
                        metavar=("BLOCK", "PRODUCER", "AUDIT"))
    parser.add_argument("--gate-stage", type=Path, required=True)
    args = parser.parse_args()
    delivery = args.delivery.resolve()
    details = json.loads((delivery / "delivery.json").read_text())
    assert sorted(row[0] for row in args.candidate) == ["C", "F", "U"]
    assert set(details["blocks"]) == {"C", "F", "U"}
    files = {}

    def include(path, expected=None):
        path = Path(path).resolve(strict=True)
        assert path.is_file() and path.is_relative_to(ROOT)
        name = path.relative_to(ROOT).as_posix()
        if name not in files:
            files[name] = (path, sha(path))
        if expected:
            assert files[name][1] == expected, name

    source_stages = set()
    for block, producer, audit in args.candidate:
        prod, audit = Path(producer).resolve(), Path(audit).resolve()
        inputs, completion, acceptance = prod / "inputs.json", prod / "completion.json", audit / "receipt.json"
        record = json.loads(acceptance.read_text())
        assert record["passed"] and record["input_receipt_sha256"] == sha(completion)
        members = details["blocks"][block]["members"]
        assert members["physical-receipt.json"] == sha(acceptance)
        assert members["producer-receipt.json"] == sha(completion)
        include(inputs, members["producer-inputs.json"])
        include(completion)
        include(acceptance)
        for name, digest in json.loads(inputs.read_text()).items():
            path = Path(name)
            if path.suffix in SOURCE_SUFFIX:
                include(path, digest)
                if (path.parent / "stage.json").is_file():
                    source_stages.add(path.parent)
        completed = json.loads(completion.read_text())
        final_dir, = {Path(path).parent for path in completed["outputs"]}
        snapshots = completed["resumed_checkpoint_sha256"]
        for name in ("4_cts.odb", "4_cts.sdc", "5_1_grt.odb", "5_1_grt.sdc", "original-route.guide"):
            path = final_dir / name
            if name.startswith("4_cts") or str(path) in snapshots:
                include(path, snapshots.get(name) or snapshots[str(path)])
        source_stages.add(audit.parent)
        for name in ("resume_route.py", "resume_c_post_grt.py", "c_loads_batch.sh", "c_post_grt_batch.sh"):
            path = prod.parent / name
            if path.is_file():
                include(path)
        for name in ("physical.tcl", "sta.tcl", "native-drc.tcl", "lef.tcl", "stream-inventory.tcl"):
            path = audit / name
            if path.is_file():
                include(path)
    for stage in source_stages:
        manifest = stage / "stage.json"
        include(manifest)
        for name, record in json.loads(manifest.read_text()).items():
            include(stage / name, record["sha256"])
    for name in ("tb_block_ucf16.sv", "gate_regression.sh", "package_accepted.py", "package_sources.py"):
        include(args.gate_stage / name)
    # Copies of identical source are stored once. The manifest retains each
    # original project-relative path so a reviewer can reconstruct the tree.
    by_sha = {digest: path for path, digest in files.values()}
    manifest = json.dumps({"root": str(ROOT), "files": {name: row[1] for name, row in sorted(files.items())}},
                          indent=2).encode() + b"\n"
    target = delivery / "execution-source.tar.gz"
    assert not target.exists()
    with tarfile.open(target, "w:gz", compresslevel=3) as out:
        entry = tarfile.TarInfo("source-manifest.json")
        entry.size = len(manifest)
        out.addfile(entry, io.BytesIO(manifest))
        for digest, path in sorted(by_sha.items()):
            out.add(path, arcname="sha256/" + digest, recursive=False)
    (delivery / "execution-source.sha256").write_text(f"{sha(target)}  {target.name}\n")


if __name__ == "__main__":
    main()
