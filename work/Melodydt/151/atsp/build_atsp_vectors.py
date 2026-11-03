#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent integer fixtures for L4-A-TSP; Python 3.7+, no RTL execution.

The oracle is componentwise signed16 saturating ADD, not a control/RTL model.
Wo is an external integer cut, not a computed attention projection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import struct
import sys

HERE = Path(__file__).resolve().parent
FIXTURES = ("plain", "dense", "saturation")
H = 1024
TOKENS = 2
LANES = 8
WORDS = 256
WORD_BYTES = 16
SAT_FIRST_WORD = "000080007fff0000ffffffff80007fff"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n").encode("utf-8")


def add_s16(a, b):
    """Exact integer sum, with one final saturation; no rounding or wrapping."""
    if not (-32768 <= a <= 32767 and -32768 <= b <= 32767):
        raise ValueError("operand outside signed16")
    value = a + b
    if value > 32767:
        return 32767, True
    if value < -32768:
        return -32768, True
    return value, False


def mix32(value):
    """Specified deterministic pattern, not a library RNG or trained data."""
    value = (value ^ (value >> 16)) & 0xffffffff
    value = (value * 0x7feb352d) & 0xffffffff
    value = (value ^ (value >> 15)) & 0xffffffff
    value = (value * 0x846ca68b) & 0xffffffff
    return (value ^ (value >> 16)) & 0xffffffff


def operands(name):
    x, wo = [], []
    boundary_pairs = (
        (32767, 1), (-32768, -1), (32767, -32768), (-32768, 32767),
        (0, 0), (16384, 16384), (-16384, -16384), (12345, -12345),
        (32760, 8), (-32760, -9), (32767, 0), (-32768, 0),
        (1, -2), (-1, 2), (10000, 20000), (-10000, -20000),
    )
    for token in range(TOKENS):
        for channel in range(H):
            if name == "plain":
                a = ((channel * 73 + token * 1009) % 8192) - 4096
                b = ((channel * 29 + token * 53) % 2048) - 1024
            elif name == "dense":
                seed = token * H + channel
                a = mix32(seed ^ 0x13579bdf) % 32001 - 16000
                b = mix32(seed ^ 0x2468ace0) % 24001 - 12000
            elif name == "saturation":
                group, lane = divmod(channel, LANES)
                a, b = boundary_pairs[(13 * group + lane + 3 * token) % 16]
            else:
                raise ValueError("unknown fixture")
            x.append(a)
            wo.append(b)
    return x, wo


def pack_values(values):
    if len(values) != TOKENS * H:
        raise ValueError("must retain actual two rows of H1024")
    return struct.pack("<2048h", *values)


def hex_words(raw):
    if len(raw) != WORDS * WORD_BYTES:
        raise ValueError("payload is not 256 words")
    # readmemh word spelling: lane0 in low16, byte0 is low8 of lane0.
    return ("".join(raw[i:i + WORD_BYTES][::-1].hex() + "\n"
                    for i in range(0, len(raw), WORD_BYTES))).encode("ascii")


def interleave_words(raw):
    """Pure index mapping T[2*g+t] = token_major[t*128+g]."""
    return b"".join(raw[(t * 128 + g) * 16:(t * 128 + g + 1) * 16]
                    for g in range(128) for t in range(2))


def payloads(name):
    x, wo = operands(name)
    scalar_results = [add_s16(a, b) for a, b in zip(x, wo)]
    expected = [value for value, clipped in scalar_results]
    xb, wb, eb = pack_values(x), pack_values(wo), pack_values(expected)
    files = {
        "x.hex": hex_words(xb), "wo.hex": hex_words(wb),
        "expected-output.hex": hex_words(eb),
        "x.bin": xb, "wo.bin": wb, "expected.bin": eb,
        "wo-interleaved.bin": interleave_words(wb),
    }
    return files, {
        "saturated_elements": sum(int(clip) for value, clip in scalar_results),
        "expected_done_saturated": any(clip for value, clip in scalar_results),
        "output_nonzero_elements": sum(value != 0 for value in expected),
        "output_min": min(expected), "output_max": max(expected),
    }


def mathematical_self_check():
    """Literal boundaries + independently specified order/packing identities."""
    literals = (
        (0, 0, 0, False), (32767, 0, 32767, False),
        (-32768, 0, -32768, False), (32767, 1, 32767, True),
        (-32768, -1, -32768, True), (16384, 16384, 32767, True),
        (-16384, -16384, -32768, False), (32767, -32768, -1, False),
        (-32768, 32767, -1, False), (12345, -12345, 0, False),
        (-1, 2, 1, False), (1, -2, -1, False),
        (32760, 7, 32767, False), (-32760, -8, -32768, False),
        (32760, 8, 32767, True), (-32760, -9, -32768, True),
    )
    for a, b, out, clip in literals:
        if add_s16(a, b) != (out, clip):
            raise AssertionError("literal arithmetic boundary mismatch")
    # Zero is the identity for every signed16 raw value; endpoint overflow
    # occurs only beyond, not at, the representable endpoint.
    for a in range(-32768, 32768):
        if add_s16(a, 0) != (a, False):
            raise AssertionError("zero identity mismatch")
        if add_s16(a, 32767 - a if a >= 0 else -32768 - a) != (
                32767 if a >= 0 else -32768, False):
            raise AssertionError("exact endpoint mismatch")
    manual_lanes = [32767, -32768, -1, -1, 0, 32767, -32768, 0]
    manual_bytes = bytes.fromhex("ff7f0080ffffffff0000ff7f00800000")
    if struct.pack("<8h", *manual_lanes) != manual_bytes:
        raise AssertionError("literal little-endian word mismatch")
    if manual_bytes[::-1].hex() != SAT_FIRST_WORD:
        raise AssertionError("literal readmemh word mismatch")
    order = [t * 128 + g for g in range(128) for t in range(2)]
    if len(set(order)) != 256 or order[:4] != [0, 128, 1, 129] or order[-2:] != [127, 255]:
        raise AssertionError("interleave is not the declared complete permutation")
    all_files = []
    for name in FIXTURES:
        files, facts = payloads(name)
        if facts["expected_done_saturated"] != (name == "saturation"):
            raise AssertionError("fixture saturation classification changed")
        if facts["output_nonzero_elements"] == 0:
            raise AssertionError("fixture cannot be an all-zero false positive")
        for file_name in ("x.hex", "wo.hex", "expected-output.hex"):
            lines = files[file_name].decode("ascii").splitlines()
            if len(lines) != 256 or any(not re.fullmatch("[0-9a-f]{32}", s) for s in lines):
                raise AssertionError("hex length/width is wrong")
        if name == "saturation" and files["expected-output.hex"].splitlines()[0].decode("ascii") != SAT_FIRST_WORD:
            raise AssertionError("hand-calculated saturated first word mismatch")
        all_files.append(files)
    if len(set(item["expected.bin"] for item in all_files)) != 3:
        raise AssertionError("fixture outputs must remain distinct across reuse")
    return {"literal_add_boundaries": len(literals),
            "all_s16_zero_identity_values": 65536,
            "all_s16_exact_endpoint_values": 65536,
            "manual_word_and_interleave": "PASS", "fixture_math": "PASS"}


def validate_contract(contract):
    if contract["fixture_ids"] != list(FIXTURES):
        raise ValueError("fixture ID/order contract mismatch")
    if contract["shape"] != {"H": 1024, "tokens": 2, "lanes_per_word": 8,
                             "words_per_fixture": 256, "bytes_per_binary": 4096}:
        raise ValueError("fixed real-dimensional cut was changed")
    for name in FIXTURES:
        files, facts = payloads(name)
        frozen = contract["fixtures"][name]
        if facts != frozen["expected_facts"]:
            raise ValueError("frozen fixture facts differ: " + name)
        for filename, data in files.items():
            if frozen["files"][filename] != {"bytes": len(data), "sha256": sha256(data)}:
                raise ValueError("frozen fixture SHA differs: " + name + "/" + filename)


def write_new(output, source_commit, self_checks, contract):
    if output.exists():
        raise ValueError("output already exists; choose a fresh directory or --check")
    output.mkdir(parents=True)
    entries = []
    for name in FIXTURES:
        (output / name).mkdir()
        files, facts = payloads(name)
        entries.append({"id": name, "directory": name,
                        "expected_done_saturated": facts["expected_done_saturated"],
                        "expected_facts": facts,
                        "files": {n: {"path": name + "/" + n, "bytes": len(d), "sha256": sha256(d)}
                                  for n, d in sorted(files.items())},
                        "binary_dumps": contract["fixtures"][name]["binary_dumps"]})
        for filename, data in files.items():
            (output / name / filename).write_bytes(data)
    indices = [{"t_word": 2 * g + t, "token": t, "group": g,
                "tokenmajor_word": t * 128 + g}
               for g in range(128) for t in range(2)]
    index_data = json_bytes({"meaning": "pure payload permutation, not an RTL state trace", "words": indices})
    (output / "t-spool-index.json").write_bytes(index_data)
    manifest = {"schema_version": 1, "status": "GENERATED_INTEGER_GOLDEN_NOT_RTL",
                "scope": contract["scope"], "shape": contract["shape"],
                "source_commit_caller_declared": source_commit,
                "builder_sha256": sha256(Path(__file__).read_bytes()),
                "contract_sha256": sha256((HERE / "fixture-contract.json").read_bytes()),
                "python": platform.python_version(), "self_checks": self_checks,
                "fixtures": entries,
                "t_spool_index": {"path": "t-spool-index.json", "bytes": len(index_data), "sha256": sha256(index_data)}}
    (output / "fixture-index.json").write_bytes(json_bytes(manifest))
    return manifest


def check_existing(output, source_commit, contract):
    manifest = json.loads((output / "fixture-index.json").read_text(encoding="utf-8"))
    if manifest["builder_sha256"] != sha256(Path(__file__).read_bytes()):
        raise ValueError("existing fixture builder source differs")
    if manifest["contract_sha256"] != sha256((HERE / "fixture-contract.json").read_bytes()):
        raise ValueError("existing fixture contract differs")
    if source_commit is not None and manifest["source_commit_caller_declared"] != source_commit:
        raise ValueError("source commit declaration differs")
    if [entry["id"] for entry in manifest["fixtures"]] != list(FIXTURES):
        raise ValueError("existing fixture IDs/order differ")
    for entry in manifest["fixtures"]:
        files, facts = payloads(entry["id"])
        if facts != entry["expected_facts"]:
            raise ValueError("existing fixture facts differ")
        for filename, expected in files.items():
            actual = (output / entry["id"] / filename).read_bytes()
            if actual != expected or entry["files"][filename]["sha256"] != sha256(actual):
                raise ValueError("existing fixture data/SHA differ: " + filename)
    index_data = (output / "t-spool-index.json").read_bytes()
    if manifest["t_spool_index"]["sha256"] != sha256(index_data):
        raise ValueError("spool index SHA differs")
    if [x["tokenmajor_word"] for x in json.loads(index_data.decode("utf-8"))["words"]] != [t * 128 + g for g in range(128) for t in range(2)]:
        raise ValueError("spool index permutation differs")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", "--output-dir", required=True, type=Path)
    parser.add_argument("--source-commit", help="actual caller code commit, 40 hexadecimal digits")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--check", action="store_true", help="read-only check of an existing generated directory")
    args = parser.parse_args()
    if args.source_commit is not None and not re.fullmatch("[0-9a-fA-F]{40}", args.source_commit):
        parser.error("--source-commit requires the actual full 40-digit commit")
    contract = json.loads((HERE / "fixture-contract.json").read_text(encoding="utf-8"))
    validate_contract(contract)
    self_checks = mathematical_self_check() if args.self_check else {"status": "NOT_REQUESTED"}
    output = args.output.resolve()
    manifest = (check_existing(output, args.source_commit, contract) if args.check else
                write_new(output, args.source_commit, self_checks, contract))
    print(json.dumps({"status": "PASS_ATSP_VECTOR_STATIC_CHECK_NOT_RTL", "mode": "check" if args.check else "generate",
                      "output": str(output), "fixture_count": len(manifest["fixtures"]),
                      "binary_expected_bytes_each": 4096, "self_checks": self_checks,
                      "fixture_index_sha256": sha256((output / "fixture-index.json").read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, AssertionError, OSError, KeyError) as error:
        print("FAIL_ATSP_VECTOR_STATIC_CHECK: " + str(error), file=sys.stderr)
        sys.exit(1)
