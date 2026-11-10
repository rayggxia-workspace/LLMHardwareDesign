"""Verify exact frozen E32 unit vectors, strict build and result receipts."""
import argparse
import hashlib
import json
from pathlib import Path

from audit_p_scope import unpack


def audit(root):
    rows = []
    for row in json.loads((root / "index.json").read_text(encoding="utf-8"))["runs"]:
        source, logs = (unpack(root, row, k) for k in ("source", "receipts"))
        assert source["source/source-commit.txt"].decode().strip() == row["source_commit"]
        for name, digest in json.loads(logs["receipts-manifest.json"]).items():
            assert hashlib.sha256(logs[name]).hexdigest() == digest
        for line in logs["source.sha256"].decode().splitlines():
            digest, name = line.split("  ", 1)
            assert hashlib.sha256(source["source/" + name]).hexdigest() == digest
        reports = [json.loads(v) for name, v in logs.items() if name.endswith("/result.json")]
        if row["state"] == "COMPLETED":
            assert {r["seed"] for r in reports} == set(range(25001, 25007))
            for report in reports:
                prefix = f"seed-{report['seed']}/"
                assert b"%Warning" not in logs[prefix + "build.log"]
                assert len(logs[prefix + "vectors.hex"].splitlines()) == 768
                for name, digest in report["hashes"].items():
                    assert hashlib.sha256(logs[prefix + name]).hexdigest() == digest
                assert {r["initial"] for r in report["results"]} == {0, 1, 2}
                for result in report["results"]:
                    line = result["receipt"]
                    trace = logs[prefix + f"initial-{result['initial']}.log"].decode()
                    assert trace.splitlines().count(line) == 1
                    assert line.startswith("PASS e_s32_native commands=768 returned=768 ")
                    fields = dict(v.split("=", 1) for v in line.split()[2:])
                    assert int(fields["malformed"]) > 0 and int(fields["held"]) > 0
                    assert fields["reset_partial"] == "1"
        else:
            assert not reports and b"%Warning-PROCASSINIT" in logs["seed-25001/build.log"]
        rows.append(dict(job=row["job"], state=row["state"],
                         trials=sum(len(r["results"]) for r in reports)))
    return dict(runs=rows, qualification="E32 exact pointwise core only; no S/LC/STA")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    print(json.dumps(audit(parser.parse_args().root)))
