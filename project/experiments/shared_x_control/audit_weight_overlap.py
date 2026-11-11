"""Audit paired early EXEC timings and actual DMA cancellation receipts."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from archive_transport import open_archive
from audit_weight_prefill import check_scope, traces


def read_source_hashes(path):
    with open_archive(path) as archive:
        manifest, = (m for m in archive.getnames() if m.endswith("/results/source.sha256"))
        prefix = manifest.removesuffix("/results/source.sha256")
        hashes = {}
        for line in archive.extractfile(manifest).read().decode().splitlines():
            expected, filename = line.split("  ", 1)
            if filename.endswith("/s_sram_256x128_freepdk45.v"):
                assert expected == "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7"
                continue
            if filename.startswith("/"):
                _, relative = re.split(r"/issue250-control-prep-[0-9-]+/", filename, maxsplit=1)
                member = "./" + relative
            else:
                member = prefix + "/" + filename
            assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == expected, member
            hashes[member] = expected
        return hashes


def compare_scopes(rows):
    event = lambda name: [r for r in rows if r[1] == name]
    by_id = lambda name: {r[3]: r[0] for r in event(name)}
    records = event("RECORD")
    first, second = records[::2], records[1::2]
    assert len(first) == len(second) == 128
    assert all(a[4] == b[4] and a[5] != b[5] for a, b in zip(first, second, strict=True))
    fill = by_id("W_FILL")
    issue = by_id("M_EXEC")
    early = [(a[3], b[3], fill[b[3]] - issue[a[3]]) for a, b in zip(first, second, strict=True)
             if issue[a[3]] < fill[b[3]]]
    info, addresses = check_scope(rows, limited_peer=False)
    info.update(early_older_exec_count=len(early), early_older_exec_lead_cycles=[x[2] for x in early])
    return info, addresses


def audit_cancel(rows, expected_drains):
    start, = (r for r in rows if r[1] == "CANCEL_FOUR")
    terminal, = (r for r in rows if r[1] == "CANCEL_DONE")
    assert start[2] == terminal[2] == 2
    assert terminal[0] - start[0] == terminal[3]
    assert terminal[4] == expected_drains and terminal[5] >= expected_drains
    assert not any(e == "M_EXEC" and s == 2 and c >= start[0] for c, e, s, *_ in rows)
    assert sum(e == "M_EXEC" and s == 3 for _, e, s, *_ in rows) == 256
    assert sum(e == "S_ACK" and s == 3 for _, e, s, *_ in rows) == 32
    generations = [r[3] for r in rows if r[1] == "DDR_PURGE_REQ"]
    assert generations == [r[3] for r in rows if r[1] == "DDR_PURGE_DONE"] and len(generations) > 1
    requests = Counter((r[3] // 2, r[4]) for r in rows if r[1] == "DDR_BACKEND_REQ")
    returns = Counter((r[3] // 2, r[4]) for r in rows if r[1] == "DDR_BACKEND_RSP")
    assert requests == returns and max(requests.values()) == 1
    return dict(drain_cycles=terminal[3], cancelled_W_banks=terminal[4], failed_range_records=terminal[5],
                actual_purges=len(generations), actual_DDR_beats=len(requests))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal", type=Path, required=True)
    parser.add_argument("--cancel-before-exec", type=Path, required=True)
    parser.add_argument("--cancel-during-exec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = [traces(p) for p in (args.normal, args.cancel_before_exec, args.cancel_during_exec)]
    cases = [(s, i) for s in range(1, 7) for i in range(3)]
    for modes, trial_data in zip(((6, 7), (7,), (7,)), data, strict=True):
        assert set(trial_data) == {(m, s, i) for m in modes for s, i in cases}
    rows = []
    for seed, initial in cases:
        result = {"seed": seed, "initial": initial, "before": [], "after": []}
        for scope in (0, 1):
            old, new = (compare_scopes([r for r in data[0][m, seed, initial] if r[2] == scope]) for m in (6, 7))
            assert old[1] == new[1]
            assert old[0]["early_older_exec_count"] == 0 and new[0]["early_older_exec_count"] > 0
            result["before"].append(old[0])
            result["after"].append(new[0])
        result["before_cycles"] = 1 + sum(s["cycles"] for s in result["before"])
        result["after_cycles"] = 1 + sum(s["cycles"] for s in result["after"])
        result["saved_fraction"] = 1 - result["after_cycles"] / result["before_cycles"]
        assert result["saved_fraction"] > 0
        result["cancel_before_exec"] = audit_cancel(data[1][7, seed, initial], 4)
        result["cancel_during_exec"] = audit_cancel(data[2][7, seed, initial], 3)
        rows.append(result)
    files = {p.name: dict(archive_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                          source_hashes=read_source_hashes(p))
             for p in (args.normal, args.cancel_before_exec, args.cancel_during_exec)}
    args.output.write_text(json.dumps(dict(pass_count=len(rows), trials=rows, inputs=files), indent=2) + "\n",
                           encoding="utf-8")
    fields = ("before_cycles", "after_cycles", "saved_fraction")
    print(json.dumps({field: [min(r[field] for r in rows), max(r[field] for r in rows)] for field in fields}))


if __name__ == "__main__":
    main()
