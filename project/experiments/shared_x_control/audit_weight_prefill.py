"""Independent conservation and cycle audit of archived wide-P W traces."""
import argparse
import collections
import csv
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path


def traces(path):
    result = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            key = re.search(r"/p-resident-([4567])-([1-6])-([0-2])\.csv$", member.name)
            if key is None:
                continue
            assert member.isfile()
            with io.TextIOWrapper(archive.extractfile(member), encoding="utf-8") as raw:
                result[tuple(map(int, key.groups()))] = [
                    (int(c), e, int(scope), int(tag), int(d), int(v))
                    for c, e, scope, tag, d, v in list(csv.reader(raw))[1:]
                ]
    return result


def check_scope(rows, limited_peer):
    by_event = collections.defaultdict(list)
    pending = set()
    bank_counts = collections.Counter()
    peak_banks = 0
    for cycle, event, _, identity, detail, value in rows:
        by_event[event].append((cycle, identity, detail, value))
        if event == "DDR_REQ":
            assert identity not in pending
            pending.add(identity)
            bank_counts[(identity >> 21) & 3] += 1
            peak_banks = max(peak_banks, len(bank_counts))
        elif event == "DDR_RSP":
            pending.remove(identity)
            bank = (identity >> 21) & 3
            bank_counts[bank] -= 1
            if not bank_counts[bank]:
                del bank_counts[bank]
    assert not pending
    assert len(by_event["DDR_REQ"]) == len(by_event["DDR_RSP"]) == 4352
    assert len(by_event["A_S_REQ"]) == 256 and len(by_event["S_ACK"]) == 32
    sequence = ["RECORD", "W_ALLOC", "W_FILL", "M_EXEC", "COMPLETE"]
    time = [{i: c for c, i, _, _ in by_event[event]} for event in sequence]
    assert all(len(x) == 256 for x in time)
    assert all(time[0].keys() == x.keys() for x in time)
    assert all(all(a[i] < b[i] for a, b in zip(time, time[1:])) for i in time[0])
    assert len(by_event["CASE_DONE"]) == 1
    info = {"cycles": by_event["CASE_DONE"][0][1], "peak_real_inflight_W_banks": peak_banks}
    reply_cycles = [row[0] for row in by_event["DDR_RSP"]]
    if limited_peer:
        gaps = [b - a for a, b in zip(reply_cycles, reply_cycles[1:])]
        assert min(gaps) == 2
        info["extra_cycles_between_first_last_W_return_above_two_cycle_peer_floor"] = sum(n - 2 for n in gaps)
    else:
        assert len(by_event["DDR_BACKEND_REQ"]) == len(by_event["DDR_BACKEND_RSP"]) == 4352
        pending = {}
        issues_by_ch = [collections.Counter(), collections.Counter()]
        for c, event, _, lane, tag, _ in rows:
            if event == "DDR_BACKEND_REQ":
                assert tag not in pending
                pending[tag] = lane // 2
                issues_by_ch[lane // 2][c] += 1
            elif event == "DDR_BACKEND_RSP":
                assert pending.pop(tag) == lane // 2
        assert not pending
        rolling = [max(v + d[c + 1] + d[c + 2] for c, v in d.items()) for d in issues_by_ch]
        assert max(rolling) <= 4
        info["backend_true_issue_peak_3_cycles_each_channel"] = rolling
    return info, collections.Counter(row[2] for row in by_event["DDR_REQ"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compare", type=Path, nargs="+", required=True)
    p.add_argument("--cancel", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--global-peer", action="store_true")
    args = p.parse_args()
    sets = {}
    for archive in args.compare:
        for key, value in traces(archive).items():
            assert key not in sets
            sets[key] = value
    expected_modes = (4, 6) if args.global_peer else (4, 5, 6)
    cancel_sets = traces(args.cancel)
    paired = []
    for seed in range(1, 7):
        for init in range(3):
            row = {"seed": seed, "initial_state": init, "modes": {}}
            for scope in (0, 1):
                base = None
                for mode in expected_modes:
                    events = [r for r in sets[mode, seed, init] if r[2] == scope]
                    info, addresses = check_scope(events, not args.global_peer)
                    if base is None:
                        base = addresses
                    else:
                        assert addresses == base
                    row["modes"].setdefault(mode, []).append(info)
            source = cancel_sets[6, seed, init]
            start, = (c for c, e, _, _, _, _ in source if e == "CANCEL_FOUR")
            terminal, = (r for r in source if r[1] == "CANCEL_DONE")
            assert terminal[0] - start == terminal[3] and terminal[4] == 4 and terminal[5] >= 4
            assert not any(e == "M_EXEC" for c, e, k, *_ in source if k == 2 and c >= start)
            assert sum(e == "M_EXEC" and k == 3 for _, e, k, *_ in source) == 256
            assert sum(e == "S_ACK" and k == 3 for _, e, k, *_ in source) == 32
            row["cancel"] = {"cycles_to_terminal": terminal[3], "true_drains": terminal[4],
                             "cancelled_records": terminal[5]}
            if args.global_peer:
                requests = [r[3] for r in source if r[1] == "DDR_PURGE_REQ"]
                dones = [r[3] for r in source if r[1] == "DDR_PURGE_DONE"]
                assert requests == dones and len(requests) > 1
                assert sum(r[1] == "DDR_BACKEND_REQ" for r in source) == 13396
                assert sum(r[1] == "DDR_BACKEND_RSP" for r in source) == 13396
                row["cancel"]["actual_purges_in_entire_run"] = len(dones)
            original = sum(r["cycles"] for r in row["modes"][4]) + 1
            row["total_cycles_including_one_cycle_setup"] = {
                mode: sum(r["cycles"] for r in data) + 1 for mode, data in row["modes"].items()}
            row["saved_cycle_fraction_vs_mode4"] = {
                mode: 1 - cycles / original for mode, cycles in row["total_cycles_including_one_cycle_setup"].items()}
            paired.append(row)
    assert set(sets) == {(m, s, i) for m in expected_modes for s in range(1, 7) for i in range(3)}
    expected_peaks = {4: 1, 5: 2, 6: 4}
    assert all(all(max(x["peak_real_inflight_W_banks"] for x in row["modes"][m]) == expected_peaks[m]
                   for m in expected_modes) for row in paired)
    summary = {"scope": "one real wide P (K2048, Gate N64 + Up N64), two scopes; not full FFN",
               "dma_peer": "real global fabric, finite external DDR peer" if args.global_peer
               else "direct finite peer; at most one accepted response per two cycles",
               "pass": True, "paired": paired, "inputs": {
                   path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [*args.compare, args.cancel]}}
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"paired": len(paired), "total_cycles": {m: [
        min(r["total_cycles_including_one_cycle_setup"][m] for r in paired),
        max(r["total_cycles_including_one_cycle_setup"][m] for r in paired)] for m in expected_modes},
        "cancel_cycles": [min(r["cancel"]["cycles_to_terminal"] for r in paired),
                          max(r["cancel"]["cycles_to_terminal"] for r in paired)]}))


if __name__ == "__main__":
    main()
