"""Offline archive and transaction audit for real-S FFN Mid and E32."""
import argparse
import hashlib
import json
from pathlib import Path

from audit_p_scope import unpack


def fields(line):
    return dict((k, int(v)) for k, v in (part.split("=", 1) for part in line.split()[1:]))


def raw_pass(line, prefix):
    assert line.startswith(prefix)
    return fields(line.removeprefix("PASS "))


def audit(root, cache):
    runs = []
    for r in json.loads((root / "index.json").read_text(encoding="utf-8"))["runs"]:
        source, logs = (unpack(root, r, k, cache) for k in ("source", "receipts"))
        assert source["source/source-commit.txt"].decode().strip() == r["source_commit"]
        manifest = json.loads(logs["receipts-manifest.json"])
        for path, digest in manifest.items():
            assert hashlib.sha256(logs[path]).hexdigest() == digest
        for line in logs["source.sha256"].decode().splitlines():
            digest, path = line.split("  ", 1)
            assert hashlib.sha256(source["source/" + path]).hexdigest() == digest
        reports = [json.loads(v) for k, v in logs.items() if k.endswith("/result.json")]
        mapped = [json.loads(v) for k, v in logs.items() if k.endswith("/receipt.json")]
        if r["state"] == "FAILED":
            assert not reports and not mapped
            assert b"%Error" in logs["seed-25001/build.log"]
        elif mapped:
            assert not reports and len(mapped) == 2
            for m in mapped:
                assert m["passed"] and m["mapped"] and not m["physical_qualified"]
                assert m["rtl_trials"] == 36 and m["instantiated_sram_bytes"] == 0
                assert m["liberty_sha256"] == "8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1"
                for path, digest in m["source_sha256"].items():
                    assert hashlib.sha256(source["source/" + path]).hexdigest() == digest
                for path, digest in m["reused_artifacts"]["artifacts"].items():
                    relative = path.split(r["remote_root"] + "/", 1)[1]
                    assert hashlib.sha256(logs[relative]).hexdigest() == digest
        else:
            assert len(reports) == 6 and {v["seed"] for v in reports} == set(range(25001, 25007))
            for q in reports:
                base = f"seed-{q['seed']}/"
                assert b"%Warning" not in logs[base + "build.log"]
                for name, digest in q["hashes"].items():
                    assert hashlib.sha256(logs[base + name]).hexdigest() == digest
                assert {(x["mode"], x["initial"]) for x in q["results"]} == {
                    (m, i) for m in (0, 1) for i in range(3)}
                for v in q["results"]:
                    lines = logs[base + v["log"]].decode().splitlines()
                    if r["family"] == "ffnmid":
                        stripes = [fields(x) for x in lines if x.startswith("FFN_STRIPE ")]
                        mids = [fields(x) for x in lines if x.startswith("FFN_MID ")]
                        assert [x["first"] for x in stripes] == list(range(0, 11008, 192))
                        assert [x["width"] for x in stripes] == [192] * 57 + [64]
                        assert [x["tile"] for x in mids] == list(range(86))
                        assert [x["owner"] for x in mids] == [i % 3 for i in range(86)]
                        assert all(x["mode"] == v["mode"] for x in stripes + mids)
                        p, = [raw_pass(x, "PASS ffn_mid_ring_joint ") for x in lines if x.startswith("PASS ")]
                        assert p["copy_ack"] == 5504 and p["GQ_reads"] == 8256 and p["GQ_writes"] == 4128
                        assert p["tiles"] == 86 and p["columns"] == 11008 and p["actual_banks"] == 12
                    else:
                        ops = [fields(x) for x in lines if x.startswith("E_REAL_S ")]
                        assert len(ops) == 100 and all(x["mode"] == v["mode"] for x in ops)
                        assert all(x["rd"] + x["wr"] == x["ack"] and
                                   ((x["ack"] == 0) == bool(x["error"])) for x in ops)
                        p, = [raw_pass(x, "PASS e_s128_joint ") for x in lines if x.startswith("PASS ")]
                        assert p["legal"] + p["bad"] == 100 and p["actual_banks"] == 4
                        assert p.get("aperture", 128) == q.get("aperture", 128)
                    assert p["extra_SRAM"] == 0 and p["mode"] == v["mode"]
        runs.append(dict(job=r["job"], state=r["state"], trials=sum(len(q["results"]) for q in reports),
                         mappings=[dict(top=m["top"], bits=m["signal_bits"], area=m["mapped_area_um2"]) for m in mapped]))
    return dict(passed=True, runs=runs)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--receipt-cache", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(audit(a.root, a.receipt_cache)))
