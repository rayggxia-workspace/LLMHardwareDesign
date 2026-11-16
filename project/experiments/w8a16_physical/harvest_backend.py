"""Copy bounded backend evidence, preserving exact bytes and all failure logs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile


def remote(command):
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", "yuzelu@10.129.166.172", command],
                            capture_output=True, check=True)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt_dir", type=Path)
    parser.add_argument("--max-depth", type=int, help="Bound report depth, e.g. 2 keeps producer top-level stage logs")
    args = parser.parse_args()
    submission = json.loads((args.receipt_dir/"submission.json").read_text())
    root = submission["remote_root"]
    assert re.fullmatch(r"/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-physical-\d{8}-\d{2}", root)
    job = submission["job"]
    assert job.isdigit()
    inventory = remote("find "+root+" -type f -printf '%s %P\\n'").decode().splitlines()
    kept, selected, skipped = {}, {}, []
    for line in inventory:
        length, name = line.split(" ", 1)
        length = int(length)
        path = Path(name)
        assert ".." not in path.parts and not path.is_absolute()
        if path.parts[0] in {"source"} or path.parts[0].startswith("tmp-"):
            continue
        if args.max_depth is not None and len(path.parts)>args.max_depth:
            skipped.append(dict(path=name,bytes=length,reason="declared report-depth bound"))
            continue
        wanted = (path.suffix in {".json", ".log", ".txt", ".tsv", ".rpt", ".ys", ".script", ".mk", ".sdc"}
                  and not any(part in {"obj", "objects"} for part in path.parts))
        graph = path.name in {"operators.json", "mapped.json", "structural.json", "reparsed.json", "unsigned.json"} or path.name.endswith(("-functional.json", "-logic.json"))
        if not wanted or graph or length > 2_000_000:
            skipped.append(dict(path=name, bytes=length))
            continue
        selected[name] = length
    if selected:
        payload = remote(shlex.join(["tar", "-cf", "-", "-C", root, "--", *sorted(selected)]))
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
            assert set(archive.getnames()) == set(selected)
            for member in archive:
                assert member.isfile() and member.size == selected[member.name]
                data = archive.extractfile(member).read()
                assert len(data) == member.size
                target = args.receipt_dir/"evidence"/member.name
                assert target.resolve().is_relative_to(args.receipt_dir.resolve())
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                kept[member.name] = dict(bytes=member.size, sha256=hashlib.sha256(data).hexdigest())
    data = remote("sacct -j "+job+" --noheader --parsable2 --format=JobID,State,ExitCode,Elapsed,TotalCPU,MaxRSS")
    (args.receipt_dir/"sacct.txt").write_bytes(data)
    index = dict(remote_root=root, job=job, source_commit=submission["source_commit"],
                 files=kept, skipped=skipped, sacct_sha256=hashlib.sha256(data).hexdigest(),
                 scope="Bounded exact-byte logs and reports; skipped large artifacts remain at source, no inferred acceptance")
    (args.receipt_dir/"index.json").write_text(json.dumps(index, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(dict(job=job, files=len(kept), skipped=len(skipped))))


if __name__ == "__main__":
    main()
