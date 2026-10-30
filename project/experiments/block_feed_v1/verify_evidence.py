"""Verify stored Issue130 raw evidence and exact tested sources without EDA."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "work/YUZE-LU/130/validation"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    binding = json.loads((BASE / "source-binding.json").read_text())
    archive = BASE / "tested-source-bytes.zip"
    assert sha(archive.read_bytes()) == binding["archive_sha256"]
    checked = 0
    with zipfile.ZipFile(archive) as z:
        for item in binding["source_hashes"]:
            tested = z.read(item["archive_path"])
            assert sha(tested) == item["sha256"]
            current = (ROOT / item["path"]).read_bytes()
            if item["matches_current_file"]:
                # Git may check text out as LF or CRLF. Archive retains the
                # EXACT original bytes; only this working-copy comparison
                # permits that declared text newline transformation.
                assert current.replace(b"\r\n", b"\n") == tested.replace(b"\r\n", b"\n")
            else:
                assert item["path"] == "project/experiments/block_feed_v1/run.py"
                assert item["archive_path"].startswith("runner-before-fixture-adaptation/")
            checked += 1
        for name in binding["selected_runs"]:
            folder = BASE / "rtl" / name
            receipt = json.loads((folder / "receipt.json").read_text())
            assert receipt["passed"] and len(receipt["runs"]) == 3
            for run in receipt["runs"]:
                raw = (folder / f"result-{run['initial_mode']}-{run['seed']}.json").read_bytes()
                assert sha(raw) == run["result_sha256"]
                assert json.loads(raw) == run["result"] and run["result"]["passed"]
            for path, digest in receipt["source_sha256"].items():
                assert any(i["model"] == name and i["path"] == path and i["sha256"] == digest
                           for i in binding["source_hashes"])
            adaptation = receipt.get("fixture_adaptation")
            if adaptation:
                original = z.read("current/" + adaptation["original"]).decode().replace("\r\n", "\n")
                adapted = original.replace(adaptation["declaration_before"], adaptation["declaration_after"])
                adapted = adapted.replace(adaptation["entry_before"], adaptation["entry_after"])
                raw = (folder / "adapted-fixture.cpp").read_bytes()
                assert sha(raw) == adaptation["generated_sha256"]
                assert raw.decode().replace("\r\n", "\n") == adapted
    index = json.loads((BASE / "remote-receive/index.json").read_text())
    for entry in index["files"]:
        assert sha((ROOT / entry["local"]).read_bytes()) == entry["sha256"]
    received = json.loads((BASE / "remote-receive/summary.json").read_text())
    assert received["passed"] and len(received["results"]) == 2
    with zipfile.ZipFile(archive) as z:
        for receipt in received["results"]:
            assert receipt["mapped"] and receipt["passed"] and not receipt["physical_qualified"]
            for path, digest in receipt["source_sha256"].items():
                assert sha(z.read("current/" + path)) == digest
    print(f"PASS: {checked} exact tested-source bindings, 18 RTL results, raw remote receipts")
    from verify_physical_evidence import verify
    physical = verify(ROOT)
    print('PASS: stored native acceptance receipts: ' + (', '.join(physical) or 'none') + '; EDA not rerun')


if __name__ == "__main__":
    main()
