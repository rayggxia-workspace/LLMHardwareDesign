"""Independently bind the recovered E32 AP64 candidate archive and six files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

PREFIX = "issue250-ephys-20261111-"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit(archive):
    with tarfile.open(archive, "r:gz") as tar:
        members = {m.name: m for m in tar.getmembers() if m.isfile()}
        assert len(members) == len([m for m in tar.getmembers() if m.isfile()])

        def read(path):
            p = PurePosixPath(path)
            if p.is_absolute():
                assert p.parts[1:5] == ("public", "home", "yuzelu", "project-circuit")
                p = PurePosixPath(*p.parts[5:])
            assert ".." not in p.parts and p.parts[0] in {PREFIX+i for i in ("01","02","03")}
            return tar.extractfile(members[str(p)]).read()

        def load(p):
            return json.loads(read(p))

        run = PREFIX+"03"
        aud = PREFIX+"02"
        acct = read(run+"/accounting.txt").decode()
        assert acct.splitlines() == ["102462|COMPLETED|0:0|00:08:18|60",
            "102488|FAILED|1:0|00:07:12|60","102497|COMPLETED|0:0|00:00:56|60"]
        bad = load(aud+"/candidate-232/audit-summary.json")
        assert not bad["passed"] and not bad["stages"]["drc"]["passed"]
        bad_drc = load(aud+"/candidate-232/drc/drc.json")
        assert "Metal Spacing" in bad_drc["native_report"] and not bad_drc["passed"]
        delivery = load(run+"/delivery/delivery.json")
        receipt = load(run+"/delivery/receipt.json")
        assert receipt["passed"] and sha(read(run+"/delivery/delivery.json")) == receipt["outputs"]["delivery.json"]
        assert delivery["native_leaf_accepted"] and delivery["top"] == "e_s32_ap64"
        assert set(delivery["final_files"]) == {"6_final."+ext for ext in ("v","sdc","def","odb","spef","gds")}
        for name, row in delivery["final_files"].items():
            data = read(row["path"])
            assert len(data) == row["bytes"] and sha(data) == row["sha256"] == receipt["outputs"][name]
        assert set(delivery["gate_receipts"]) == {"physical","drc","density","function","formal"}
        for gate, row in delivery["gate_receipts"].items():
            rp, pp = row["path"], row["report_path"]
            assert sha(read(rp)) == row["sha256"] and sha(read(pp)) == row["report_sha256"]
            r, proof = load(rp), load(pp)
            assert r["passed"] and r["outputs"][PurePosixPath(pp).name] == row["report_sha256"]
            if gate != "density":
                assert proof["passed"] and proof["source_receipt_sha256"] == delivery["source_receipt_sha256"]
            if gate == "function":
                assert {(r["mode"],r["initial"]) for r in proof["runs"]} == {(m,i) for m in (0,1) for i in range(3)}
                for trial in proof["runs"]:
                    raw = read(str(PurePosixPath(rp).parent/trial["log"]))
                    assert sha(raw) == trial["sha256"] and raw.count(b"E_REAL_S ") == 100
                    assert raw.count(b"PASS e_s128_joint ") == 1 and b"%Error" not in raw
            if gate == "drc":
                assert proof["full_deck"]["total_items"] == 0 and not proof["native_report"]
            if gate == "formal":
                assert all(proof["strict_native_lec"]["checks"].values())
        access = load(run+"/tasks/e-access/access.json")
        assert access["source_delivery_receipt_sha256"] == sha(read(run+"/delivery/receipt.json"))
        assert access["all_signal_bits"] == access["simultaneous_connected_bits"] == 158
        assert access["native_m10_obstruction_intersections"] == 0 and access["finite_full_escape_qualified"]
        assert access["passed"] and not access["m11_m12_system_qualified"]
        for row in access["stages"].values():
            assert row["passed"] and sha(read(row["path"])) == row["sha256"] and load(row["path"])["passed"]
        for p,h in access["native_final_files"].items():
            assert sha(read(p)) == h
        return dict(passed=True, archive_bytes=archive.stat().st_size, archive_sha256=sha(archive.read_bytes()),
            accounting=acct.splitlines(), stage_source_archives={i:sha(read(PREFIX+i+"/source.tar.gz")) for i in ("01","02","03")},
            selected=delivery, access=access, rejected_alternative=bad, rejected_alternative_drc=bad_drc["native_report"],
            scope="Standalone original-rule TT 300 MHz E32 AP64 plus actual all-port research M10 landing. No system route or timing.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--index", type=Path, required=True)
    a = parser.parse_args()
    result = audit(a.archive)
    result["server_archive"] = ("yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/"
        +PREFIX+"03/archive-e-physical.tar.gz")
    a.index.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("passed","archive_bytes","archive_sha256","accounting")}))


if __name__ == "__main__":
    main()
