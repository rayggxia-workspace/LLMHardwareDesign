"""Verify that duty instrumentation leaves the exact programmed FFN trace intact."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

from audit_ffn_copy_lookahead import BASELINE_SOURCE, limits, receipts, trial
from audit_ffn_copy_rearm import sha


DUTY_LINES = re.compile(rb"^(M_DUTY|M_STATE_DUTY|DDR_DUTY) .*", re.M)
TRIAL = r"seed-([0-9]+)/mode-([01])-initial-0\.log"


def fields(text):
    return {name: int(value) for name, value in re.findall(r"(\w+)=(\d+)", text)}


def array(text):
    return [int(value, 16) for value in re.findall(r"'h([0-9a-f]+)", text)]


def duty(raw):
    math, states, ddr = {}, {}, {}
    for line in DUTY_LINES.finditer(raw):
        text = line.group().decode()
        data = fields(text)
        phase = data["phase"]
        if line[1] == b"M_DUTY":
            math[phase, data["p"]] = data
        elif line[1] == b"M_STATE_DUTY":
            states[phase, data["p"]] = array(text)
        else:
            accepted, offers = text.split(" M_offers=")
            ddr[phase] = data | {"accepted_lanes": array(accepted), "M_offers": array(offers)}
    assert set(math) == set(states) == {(phase, p) for phase in (0, 1) for p in (0, 1, 2)}
    assert set(ddr) == {0, 1}
    for phase, result in ddr.items():
        assert len(result["accepted_lanes"]) == 5 and len(result["M_offers"]) == 4
        assert sum(result["accepted_lanes"]) == sum(result["M_offers"]) == result["cycles"]
        result["zero_accept_without_local_offer"] = result["accepted_lanes"][0]-result["zero_accept_with_local_offer"]
        assert result["zero_accept_without_local_offer"] >= 0
        result["accepted_beats"] = sum(i*count for i, count in enumerate(result["accepted_lanes"]))
        result["P"] = []
        for p in range(3):
            item = math[phase, p]
            histogram = states[phase, p]
            assert len(histogram) == 32 and sum(histogram) == item["cycles"] == result["cycles"]
            assert item["exec"]*8 == item["mac"] == item["feed"] and item["feed_no_W"] == item["feed_no_A"] == 0
            assert sum(item[name] for name in ("fill_W", "fill_A", "fill_both", "fill_ready")) == histogram[8]
            assert histogram[11] == 4*item["exec"]
            result["P"].append(item | {"state_cycles": histogram})
        assert sum(p["exec"] for p in result["P"]) == (44032 if phase == 0 else 22016)
        result["operand_intake_pct"] = 100*sum(p["mac"] for p in result["P"])/(3*result["cycles"])
        result["DDR_lane_duty_pct"] = 100*result["accepted_beats"]/(4*result["cycles"])
    return ddr


def audit(path, digest, commit, candidate_sha, baseline):
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
    hashes, manifests, result = {}, {}, {}
    allocation = ""
    with tarfile.open(path, "r|gz") as archive:
        for entry in archive:
            if not entry.isfile():
                continue
            name = entry.name.removeprefix("./")
            raw = archive.extractfile(entry).read()
            assert name not in hashes
            hashes[name] = sha(raw)
            if name in {"source.sha256", "candidate.sha256", "derived.sha256"}:
                manifests[name] = raw.decode()
            elif name in {"build.log", "lint.log"}:
                assert b"%Error" not in raw and b"%Warning" not in raw
            elif name == "allocation.txt":
                allocation = raw.decode()
            elif name == "candidate.tar.gz":
                assert hashes[name] == candidate_sha
                with tarfile.open(fileobj=io.BytesIO(raw)) as candidate:
                    assert candidate.pax_headers["comment"] == commit
            elif match := re.fullmatch(TRIAL, name):
                seed, pressure = map(int, match.groups())
                assert trial(raw, pressure, None) == baseline[seed, pressure, 0, None]
                result[seed, pressure] = duty(raw)
    assert "Partition=c96" in allocation and "NumCPUs=96 NumTasks=8 CPUs/Task=12" in allocation
    assert hashes["source.tar.gz"] == BASELINE_SOURCE
    for manifest in manifests.values():
        for line in manifest.splitlines():
            checksum, name = line.split("  ", 1)
            if "/duty/" in name:
                name = "duty/" + name.rsplit("/duty/", 1)[1]
            else:
                name = "source/" + name.removeprefix("./")
            assert hashes[name] == checksum
    assert set(result) == {(seed, pressure) for seed in range(25001, 25007) for pressure in (0, 1)}
    summary = {}
    for pressure in (0, 1):
        summary[pressure] = {}
        for phase in (0, 1):
            samples = [phase_data[phase] for (_, mode), phase_data in result.items() if mode == pressure]
            summary[pressure][phase] = {key: limits([sample[key] for sample in samples]) for key in
                ("cycles", "operand_intake_pct", "DDR_lane_duty_pct", "zero_accept_without_local_offer",
                 "zero_accept_with_local_offer", "zero_accept_with_backend_offer", "zero_accept_with_return")}
            summary[pressure][phase]["seed25001"] = result[25001, pressure][phase]
    return dict(passed=len(result), checked_members=len(hashes), summary=summary,
                derived_sha256={name: digest for name, digest in hashes.items() if name.startswith("duty/")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-archive-sha256", required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--candidate-source-sha256", required=True)
    args = parser.parse_args()
    baseline, _, _, _ = receipts(args.baseline, args.baseline_sha256)
    print(json.dumps(audit(args.candidate, args.candidate_archive_sha256, args.candidate_commit,
                          args.candidate_source_sha256, baseline), indent=2))


if __name__ == "__main__":
    main()
