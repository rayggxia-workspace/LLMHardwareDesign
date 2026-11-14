"""Verify the completed C639 EXEC-priority A/B and report per-mode deltas."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from compare_exec_replays import compare


TERMINAL = re.compile(r"^(PRODUCT_PAGE_TERMINAL|PRODUCT_FFN_TERMINAL|PRODUCT_FDS_TERMINAL|"
                      r"SECOND_RESIDUAL_COMMITTED|HISTORY_KV_COMPLETE) ")
PROFILE = re.compile(r"^FFN_PROFILE cycles=(\d+) (.*)$")
PASS = re.compile(r"^(PASS q projection .*?) cycles=(\d+) mode=(\d+)$")


def functional_log(path):
    terminals, profiles, totals = Counter(), [], []
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if TERMINAL.match(line):
                terminals[line.rstrip()] += 1
                continue
            profile = PROFILE.match(line)
            if profile:
                profiles.append((int(profile[1]), profile[2]))
            entry = PASS.match(line)
            if entry:
                totals.append((entry[1], int(entry[2]), int(entry[3])))
    if len(totals) != 1 or len(profiles) != 2 or sum(
        count for line, count in terminals.items() if line.startswith("PRODUCT_FFN_TERMINAL ")
    ) != 384:
        raise ValueError("incomplete C639 functional receipts in {}".format(path))
    return terminals, profiles, totals[0]


def comparable_summary(row):
    data = dict(row)
    del data["sha256"], data["write_sha256"]
    activation = dict(data["ffn_activation"])
    del activation["sha256"]
    data["ffn_activation"] = activation
    return data


def ddr_summaries(directory):
    data = json.loads((directory / "ddr-audit.json").read_bytes())
    return {Path(name).parent.name: comparable_summary(counts) for name, counts in data.items()}


def front_half(path):
    digest = sha256()
    markers = (b"M_WEIGHT ", b"FFN_LC ", b"FFN_EXEC ", b"PRODUCT_PAGE_TERMINAL ")
    with path.open("rb") as stream:
        for line in stream:
            if line.startswith(b"FFN_SCOPE call "):
                return dict(first_call=line.decode("ascii").strip(), sha256=digest.hexdigest())
            if line.startswith(markers):
                digest.update(line)
    raise ValueError("no FFN entry in {}".format(path))


def audit(baseline, candidate, base_timing, cand_timing, ffn_only):
    old, new = ddr_summaries(baseline), ddr_summaries(candidate)
    if old != new or set(old) != {"DDR-0", "DDR-1"}:
        raise ValueError("DDR conservation or committed KV digest differs")
    modes = {}
    for mode in (0, 1):
        log = "replay-{}.log".format(mode)
        t0, f0, p0 = functional_log(baseline / log)
        t1, f1, p1 = functional_log(candidate / log)
        if t0 != t1 or [f[1] for f in f0] != [f[1] for f in f1] or p0[0] != p1[0] or p0[2] != p1[2]:
            raise ValueError("functional receipt or FFN traffic differs in mode {}".format(mode))
        name = "mode-{}.json".format(mode)
        a, b = (json.loads((d / name).read_bytes()) for d in (base_timing, cand_timing))
        if a["partial"] or b["partial"]:
            raise ValueError("A/B needs full WAIT records")
        modes[mode] = compare(a, b)
        front = {"baseline": front_half(baseline / log), "candidate": front_half(candidate / log)}
        if ffn_only and front["baseline"] != front["candidate"]:
            raise ValueError("FFN-only trial changed the front-half trajectory")
        modes[mode].update(
            fixture_cycles={"baseline": p0[1], "candidate": p1[1]},
            ffn_profile_cycles={"baseline": [f[0] for f in f0], "candidate": [f[0] for f in f1]},
            qkv_terminal_audit={
                label: sha256((directory / "qkv-terminal-audit.json").read_bytes()).hexdigest()
                for label, directory in (("baseline", baseline), ("candidate", candidate))
            },
            ddr_common=old["DDR-{}".format(mode)],
            front_half=front,
        )
    return modes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("baseline_timing", type=Path)
    parser.add_argument("candidate_timing", type=Path)
    parser.add_argument("--ffn-only", action="store_true")
    args = parser.parse_args()
    result = audit(args.baseline, args.candidate, args.baseline_timing, args.candidate_timing, args.ffn_only)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
