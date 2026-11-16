"""Offline evidence audit: source SHA, every round, negatives and work equality."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile

from shared_x_analyze import analyze


def audit(root):
    members = 0
    full_traces = 0
    numeric_cases = protocol_gates = packing_cases = 0
    rounds = []
    selected = worst = None
    with tempfile.TemporaryDirectory(prefix="issue250-shared-x-audit-") as temporary:
        for number in range(1, 10):
            tag = f"{number:02d}"
            receipt = json.loads((root / ("recovery-" + tag + ".json")).read_text())
            raw = base64.b64decode(b"".join((root / ("run-" + tag + ".tar.gz.b64")).read_bytes().split()), validate=True)
            assert hashlib.sha256(raw).hexdigest() == receipt["archive_SHA256"]
            files = {}
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
                for member in archive:
                    p = PurePosixPath(member.name)
                    assert member.isfile() and not p.is_absolute() and ".." not in p.parts and member.size < 5 * 1024 * 1024
                    assert member.name not in files
                    files[member.name] = archive.extractfile(member).read()
            assert {name: hashlib.sha256(data).hexdigest() for name, data in files.items()} == receipt["members_SHA256"]
            for line in files["source.sha256"].decode().splitlines():
                expected, name = line.split(maxsplit=1)
                assert hashlib.sha256(files[name]).hexdigest() == expected
            members += len(files)
            reports = [json.loads(data) for name, data in files.items() if name.endswith("/report.json")]
            for report in reports:
                assert report["passed"] and not report.get("error")
                full_traces += sum(case["label"] == "decode512" for case in report["results"])
            if number in (1, 3):
                assert not reports
                assert not any(b"RESULT " in data for name, data in files.items() if name.endswith(".log"))
            if 4 <= number <= 8:
                out = Path(temporary) / tag
                for name, data in files.items():
                    p = out / name
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(data)
                result = analyze(out)
                assert result == json.loads((root / ("summary-" + tag + ".json")).read_text())
                if number == 8:
                    rows = {row["plan"]: row for row in result["rows"]}
                    selected = rows["S16-final-prep2"]["tokens_s"]
                    worst = rows["S16-final-bothACK2"]["tokens_s"]
                    assert selected >= result["rows"][0]["tokens_s"]
                    assert worst >= result["rows"][0]["tokens_s"]
            if number == 8:
                source = Path(__file__).resolve().parent
                for name in ("shared_x_service.inc", "shared_x_driver.py"):
                    key = "candidate/" + name if name.endswith(".inc") else name
                    assert (source / name).read_bytes().replace(b"\r\n", b"\n") == files[key].replace(b"\r\n", b"\n")
            if number == 9:
                checks = [json.loads(data) for name, data in files.items() if name.startswith("protocol-") and name.endswith(".json")]
                assert len(checks) == 6
                for check in checks:
                    assert check["passed"] and check["multirow_direct_pairing_rejected"]
                    packing_cases += len(check["cases"])
                    numeric_cases += len(check["tile_lease_cases"])
                    protocol_gates += len(check["protocol_gates"])
            rounds.append(dict(tag=tag, members=len(files), timing_configs=len(reports),
                               archive_SHA256=receipt["archive_SHA256"]))
    assert full_traces == 46
    return dict(passed=True, archives=9, members=members, full_decode_traces=full_traces,
                packing_tail_cases=packing_cases, K128_signed_replay_cases=numeric_cases,
                directed_protocol_negative_gates=protocol_gates,
                historical_baseline_tokens_s=9.21564723269,
                selected_NoPool_S16_tokens_s=selected,
                selected_worst_tested_ACK_tokens_s=worst,
                rounds=rounds,
                scope="Evidence/source/timing conservation and transport contracts; not complete native model RTL or physical acceptance")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
