"""Compare the exact full programmed FFN baseline and guarded COPY A/B."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import tarfile

from audit_ffn_copy_rearm import sha


BASELINE_SOURCE = "058b32a84fbb7b3613dcf9fa6ab5fb74685d08a740ba417f569bedf6968d1d24"
TRIAL = r"seed-([0-9]+)/mode-([01])-initial-([012])(?:-lookahead-([01]))?\.log"
PROFILE = re.compile(rb"^(?:FFN_PROFILE|DOWN_PROFILE|DMA_PROFILE|PROGRAM_PROFILE|COPY_LOOKAHEAD_PROFILE|K_PROFILE|PASS ffn_three_p_native|%Error|%Fatal).*", re.M)
TILE_COUNT = {0: 928, 1: 516}


def trial(raw, pressure, lookahead):
    profiles, tiles = {}, {}
    for match in PROFILE.finditer(raw):
        name, *fields = match.group().decode().split()
        assert not name.startswith("%"), fields
        if name == "PASS":
            assert fields == (f"ffn_three_p_native columns=11008 stripes=58 real_P_M=3 real_S_banks=16 Mid=86 "
                              f"mode={pressure} down=1 four_w=1 shared_dma=1 program=1 split_up=0 early_exec=1").split()
            profiles[name] = {}
            continue
        row = {k: int(v) for k, v in (field.split("=", 1) for field in fields)}
        if name == "K_PROFILE":
            key = row["phase"], row["scope"], row["k"]
            assert key not in tiles
            assert row["start"] <= row["need"] <= row["quant"] <= row["header"] <= row["copy"] <= row["proof"] <= row["released"]
            tiles[key] = row
        else:
            assert name not in profiles
            profiles[name] = row
    expected = {"PASS", "FFN_PROFILE", "DOWN_PROFILE", "DMA_PROFILE", "PROGRAM_PROFILE"}
    if lookahead is not None:
        expected.add("COPY_LOOKAHEAD_PROFILE")
        assert profiles["COPY_LOOKAHEAD_PROFILE"] == dict(mode=lookahead, X_reads=14848,
                X_reads_before_previous_ACK=13920*lookahead, Mid_reads=8256)
    assert set(profiles) == expected
    assert {phase: sum(key[0] == phase for key in tiles) for phase in TILE_COUNT} == TILE_COUNT
    return profiles, tiles


def receipts(path, digest, candidate_commit=None, candidate_sha=None):
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
    hashes, manifest, parsed, oracle, closure = {}, {}, {}, {}, {}
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
                manifest[name] = raw.decode()
            elif name == "lookahead/lookahead.json":
                closure = json.loads(raw)
            elif name == "allocation.txt":
                allocation = raw.decode()
            elif name in {"build.log", "lint.log"}:
                assert b"%Error" not in raw and b"%Warning" not in raw
            elif name == "candidate.tar.gz":
                assert hashes[name] == candidate_sha
                with tarfile.open(fileobj=io.BytesIO(raw)) as candidate:
                    assert candidate.pax_headers["comment"] == candidate_commit
            elif name.endswith("/oracle.json"):
                oracle[name.split("/", 1)[0]] = json.loads(raw)
            elif match := re.fullmatch(TRIAL, name):
                seed, pressure, initial = map(int, match.groups()[:3])
                lookahead = None if match[4] is None else int(match[4])
                parsed[seed, pressure, initial, lookahead] = trial(raw, pressure, lookahead)
    assert "Partition=c96" in allocation and "NumCPUs=96 NumTasks=8 CPUs/Task=12" in allocation
    if candidate_commit is not None:
        assert hashes["source.tar.gz"] == BASELINE_SOURCE
        assert set(manifest) == {"source.sha256", "candidate.sha256", "derived.sha256"}
        for entries in manifest.values():
            for line in entries.splitlines():
                checksum, name = line.split("  ", 1)
                if "/lookahead/" in name:
                    name = "lookahead/" + name.rsplit("/lookahead/", 1)[1]
                else:
                    name = "source/" + name.removeprefix("./")
                assert hashes[name] == checksum
        for name, checksum in closure.items():
            assert hashes["lookahead/" + name] == checksum
    expected = {(seed, pressure, initial, mode) for seed in range(25001, 25007)
                for pressure in range(2) for initial in range(3)
                for mode in ([None] if candidate_commit is None else [0, 1])}
    assert set(parsed) == expected
    assert set(oracle) == {f"seed-{seed}" for seed in range(25001, 25007)}
    for directory, reference in oracle.items():
        assert reference["columns"] == 11008 and reference["descriptor_count"] == 192 and reference["down"]
        for file, checksum in reference["hashes"].items():
            assert hashes[directory + "/" + file] == checksum
    vectors = {name: value for name, value in hashes.items() if re.fullmatch(r"seed-\d+/(.*\.hex|oracle\.json|program\.json)", name)}
    return parsed, vectors, closure, len(hashes)


def limits(values):
    return [min(values), statistics.median(values), max(values)]


def compare(baseline, candidate):
    base, vectors, _, base_members = baseline
    guarded, other_vectors, derived, candidate_members = candidate
    assert vectors == other_vectors
    result = {"pair_count": len(base), "baseline_members": base_members, "candidate_members": candidate_members,
              "matching_input_files": len(vectors), "derived_sha256": derived, "pressure": {}}
    for pressure in range(2):
        stage_before = {"FFN_PROFILE": [], "DOWN_PROFILE": [], "total": [], "X_COPY": [], "Mid_COPY": []}
        stage_after = {name: [] for name in stage_before}
        for seed, mode, initial, _ in base:
            if mode != pressure:
                continue
            key = seed, mode, initial
            old, old_tiles = guarded[key + (0,)]
            new, new_tiles = guarded[key + (1,)]
            original, original_tiles = base[key + (None,)]
            assert {k: v for k, v in old.items() if k != "COPY_LOOKAHEAD_PROFILE"} == original
            assert old_tiles == original_tiles and old_tiles.keys() == new_tiles.keys()
            for stage in ("FFN_PROFILE", "DOWN_PROFILE", "DMA_PROFILE", "PROGRAM_PROFILE"):
                assert {k: v for k, v in old[stage].items() if k != "cycles"} == {
                        k: v for k, v in new[stage].items() if k != "cycles"}
            for profiles, tiles, data in ((old, old_tiles, stage_before), (new, new_tiles, stage_after)):
                ffn = profiles["FFN_PROFILE"]["cycles"]
                down = profiles["DOWN_PROFILE"]["cycles"]
                data["FFN_PROFILE"].append(ffn)
                data["DOWN_PROFILE"].append(down)
                data["total"].append(ffn+down)
                for (phase, _, _), row in tiles.items():
                    data["Mid_COPY" if phase else "X_COPY"].append(row["copy"]-row["header"])
        result["pressure"][str(pressure)] = {
            "before_min_median_max": {stage: limits(data) for stage, data in stage_before.items()},
            "after_min_median_max": {stage: limits(data) for stage, data in stage_after.items()},
            "total_paired_improvement_pct_min_median_max": limits([
                100*(before-after)/before for before, after in zip(stage_before["total"], stage_after["total"], strict=True)]),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-archive-sha256", required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--candidate-source-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(compare(receipts(args.baseline, args.baseline_sha256),
        receipts(args.candidate, args.candidate_archive_sha256, args.candidate_commit, args.candidate_source_sha256)), indent=2))


if __name__ == "__main__":
    main()
