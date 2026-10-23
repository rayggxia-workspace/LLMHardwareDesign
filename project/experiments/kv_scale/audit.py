"""Readback audit using independent Fraction arithmetic and committed source bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from oracle import attention


def main():
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    p.add_argument("--replay", type=Path)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads((a.directory / "manifest.json").read_text())
    if manifest["producer"]["dirty"] or manifest["producer"]["development"]:
        raise ValueError("formal evidence cannot be a development run")
    digest = lambda raw: hashlib.sha256(raw).hexdigest()
    file_checks = 0
    for name, record in manifest["files"].items():
        data = (a.directory / name).read_bytes()
        assert len(data) == record["bytes"] and digest(data) == record["sha256"]
        if a.replay:
            assert data == (a.replay / name).read_bytes(), "scientific replay mismatch"
        file_checks += 1
    commit = manifest["producer"]["commit"]
    source_checks = 0
    for name, record in manifest["producer"]["files"].items():
        blob = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=root)
        assert digest(blob) == record["sha256"]
        assert (root / name).read_bytes() == blob
        source_checks += 1
    table = json.loads((root / "project/experiments/integer_precision/tables.json").read_text())["exp_u32_f24"]
    payload = json.loads((a.directory / "integers.json").read_text())
    values = 0
    for case in payload:
        expected = attention(case["q_i8"], case["k_i8"], case["v_i8"], case["v_exponents"],
            case["score_M_r"], case["block"], case["probability_bits"], case["allowed"], table)
        for target, oracle in zip(case["rows"], expected):
            for key, row in oracle.items():
                assert target[key] == row
                values += len(row)
    cfg = json.loads((root / "project/experiments/kv_scale/experiment.json").read_text())
    want = {(n, b, p, profile) for n in cfg["captures"] for b in cfg["block_tokens"]
            for p in cfg["probability_bits"] for profile in cfg["input_profiles"]}
    got = {(c["name"], c["block"], c["probability_bits"], c["input_profile"]) for c in payload}
    assert got == want and len(payload) == len(want)
    summary = json.loads((a.directory / "summary.json").read_text())
    assert values == summary["integer_values_checked"]
    print(json.dumps({"status": "PASS", "source_commit": commit, "source_bindings": source_checks,
        "file_hashes": file_checks, "case_coverage": len(want), "independent_integer_values": values,
        "scientific_replay": "byte-identical" if a.replay else "not requested"}))


if __name__ == "__main__":
    main()
