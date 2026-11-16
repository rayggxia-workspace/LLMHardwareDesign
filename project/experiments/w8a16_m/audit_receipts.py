"""Offline read-only audit of collected candidate arithmetic receipts."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def audit(root):
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    summary = []
    for run in index["runs"]:
        raw = base64.b64decode((root / run["archive"]).read_bytes(), validate=True)
        assert hashlib.sha256(raw).hexdigest() == run["archive_sha256"], run["archive"]
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            members = archive.getmembers()
            assert all(m.isfile() and not PurePosixPath(m.name).is_absolute()
                       and ".." not in PurePosixPath(m.name).parts for m in members)
            data = {m.name: archive.extractfile(m).read() for m in members}
        assert data["source/source-commit.txt"].decode().strip() == run["source_commit"]
        source_raw = base64.b64decode((root / run["source_archive"]).read_bytes(), validate=True)
        assert hashlib.sha256(source_raw).hexdigest() == run["source_archive_sha256"]
        with tarfile.open(fileobj=io.BytesIO(source_raw), mode="r:gz") as archive:
            members = archive.getmembers()
            assert all((m.isfile() or m.isdir()) and not PurePosixPath(m.name).is_absolute()
                       and ".." not in PurePosixPath(m.name).parts for m in members)
            frozen_source = {m.name: archive.extractfile(m).read() for m in members if m.isfile()}
        for line in data["source.sha256"].decode().splitlines():
            digest, name = line.split("  ", 1)
            source = frozen_source["source/" + name]
            assert hashlib.sha256(source).hexdigest() == digest, (run["job"], name)
        results = [json.loads(v) for k, v in data.items() if k.endswith("/result.json")]
        if run["state"] == "FAILED":
            assert not results
            assert any(b"%Error: Exiting due to" in v for k, v in data.items() if k.endswith("-build.log"))
        else:
            assert run["state"] == "COMPLETED" and len(results) == 6
            assert {r["seed"] for r in results} == set(range(25001, 25007))
            for result in results:
                prefix = "seed-" + str(result["seed"]) + "/"
                for name in ["m.log", "scale.log", "m-build.log", "scale-build.log"]:
                    assert hashlib.sha256(data[prefix + name]).hexdigest() == result["sha256"][name]
                assert "PASS scale " in result["results"]["scale"] and "PASS M " in result["results"]["m"]
        summary.append(dict(job=run["job"], state=run["state"], seeds=len(results),
                            scale_vectors=sum(r["scale_vectors"] for r in results),
                            m_beats=sum(r["m_beats"] for r in results),
                            m_responses=sum(r["m_responses"] for r in results)))
    print(json.dumps(dict(receipts_passed=True, runs=summary,
                         qualification="arithmetic unit regression only; physical_qualified=false"), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    audit(parser.parse_args().root)
