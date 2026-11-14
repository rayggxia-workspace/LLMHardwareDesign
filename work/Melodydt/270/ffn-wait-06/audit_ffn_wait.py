"""Align native FFN record, P scope, and mother WAIT edges from C639."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
from statistics import median


P_INSTANCE = re.compile(r"\.feed_forward\.ps\[([12])\]\.")
STATES = (
    "", "weight_only", "activation_only", "weight_and_activation", "weight_activation_join",
    "exec_offer", "operand_issue", "issued_until_terminal", "alloc_context_fence",
    "activation_close_release", "activation_window", "other", "pair_prepare",
)


def instance_p(name):
    match = P_INSTANCE.search(name)
    if match:
        return int(match[1])
    if ".p0.physical_node." in name:
        return 0


def interval_cycles(start, end):
    cycles, remainder = divmod(end - start, 10)
    if cycles < 0 or remainder:
        raise ValueError("invalid time interval {} to {}".format(start, end))
    return cycles


def asset_ranges(path):
    spans = []
    for line in path.read_text(encoding="ascii").splitlines():
        start, size, file = line.split(maxsplit=2)
        kind = Path(file).stem
        if kind in ("gate", "up", "down"):
            spans.append((int(start), int(start) + int(size), kind))
    if sorted(kind for _, _, kind in spans) != ["down", "gate", "up"]:
        raise ValueError("expected three FFN weight ranges")
    return spans


def read_trace(path, assets):
    scopes, spans, offers, waits = {}, defaultdict(list), {}, defaultdict(list)
    m_windows = defaultdict(list)
    weights, inflight = {}, {}
    records = defaultdict(Counter)
    digest = sha256()
    for line in path.open("rb"):
        digest.update(line)
        event = line.split(b" ", 1)[0]
        if not line.endswith(b"\n"):
            continue
        if event == b"FFN_SCOPE":
            _, edge, owner, target, group, when = line.decode("ascii").split()
            key = (int(owner, 16), int(target))
            scope = scopes.setdefault(key, {"group": int(group)})
            if edge in scope or edge not in ("call", "raw", "lc"):
                raise ValueError("invalid scope event at {}".format(key))
            if edge == "call":
                scope["group"] = int(group)
            elif int(group) != scope["group"]:
                raise ValueError("scope moved to a different FFN wave")
            scope[edge] = int(when)
        elif event == b"FFN_WAIT":
            _, page, pc, when = line.split()
            waits[int(page)].append((int(pc), int(when)))
        elif event == b"FFN_LC":
            _, instance, owner, state, start, end = line.decode("ascii").split()
            p = instance_p(instance)
            if p is not None:
                spans[(int(owner, 16), p)].append((int(state), int(start), int(end)))
        elif event == b"FFN_EXEC":
            _, instance, owner, edge, record, ticket, when = line.decode("ascii").split()
            p = instance_p(instance)
            if p is None:
                continue
            key = (int(owner, 16), p)
            if key not in scopes:
                continue
            record, ticket, when = map(int, (record, ticket, when))
            pair = (p, record, ticket)
            if edge == "offer":
                if pair in offers:
                    raise ValueError("duplicated live EXEC offer")
                offers[pair] = (key, when)
            elif edge == "complete":
                result = inflight.pop((key, record))
                records[key]["m_result_to_lc_record_complete"] += interval_cycles(result, when)
            else:
                raise ValueError("unknown EXEC trace operation")
        elif event == b"M_WEIGHT":
            _, instance, edge, when, bank, generation, record, payload = line.decode("ascii").split()
            p = instance_p(instance)
            if p is None:
                continue
            time_ps = int(when)
            if time_ps % 1000:
                raise ValueError("M edge must occur on an integral ns")
            when = time_ps // 1000
            identity = (p, int(bank), int(generation), int(record))
            if edge == "first_issue":
                address = int(payload, 16)
                kinds = [kind for start, end, kind in assets if start <= address < end]
                if kinds:
                    kind, = kinds
                    if identity in weights:
                        raise ValueError("weight record already live")
                    weights[identity] = {"kind": kind, edge: when}
            elif identity in weights:
                weight = weights[identity]
                if edge in weight:
                    raise ValueError("repeated M edge")
                weight[edge] = when
                if edge == "exec":
                    key, offer = offers.pop((p, identity[-1], int(payload, 16)))
                    weight["scope"] = key
                    weight["ticket"] = int(payload, 16)
                    summary = records[key]
                    summary["offer_to_m_exec"] += interval_cycles(offer, when)
                    summary["last_issue_to_fill"] += interval_cycles(weight["last_issue"], weight["full_fill"])
                    summary["fill_to_ack"] += interval_cycles(weight["full_fill"], weight["ack"])
                elif edge == "result":
                    key = weight["scope"]
                    if int(payload, 16) != weight["ticket"]:
                        raise ValueError("M result has a different EXEC ticket")
                    result_key = (key, identity[-1])
                    if result_key in inflight:
                        raise ValueError("duplicate M result")
                    inflight[result_key] = when
                    records[key][weight["kind"]] += 1
                    records[key]["m_exec_to_result"] += interval_cycles(weight["exec"], when)
                    m_windows[key].append((weight["exec"], when))
                    del weights[identity]
    return scopes, spans, records, waits, m_windows, (len(offers), len(weights), len(inflight)), digest.hexdigest()


def union(windows):
    merged = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return merged


def cycle_breakdown(spans, m_windows, start, end):
    states, no_m_exec = Counter(), Counter()
    m_index = 0
    for state, a, b in spans:
        a, b = max(a, start), min(b, end)
        if b <= a:
            continue
        covered = 0
        while m_index < len(m_windows):
            m_start, m_end = m_windows[m_index]
            if m_start >= b:
                break
            if m_end > a:
                covered += interval_cycles(max(a, m_start), min(b, m_end))
            if m_end > b:
                break
            m_index += 1
        cycles = interval_cycles(a, b)
        states[STATES[state]] += cycles
        no_m_exec[STATES[state]] += cycles - covered
    return states, no_m_exec


def report(path, assets, partial):
    scopes, spans, records, waits, m_windows, pending, digest = read_trace(path, asset_ranges(assets))
    groups = defaultdict(dict)
    incomplete = 0
    for key, scope in scopes.items():
        owner, p = key
        page, group = owner >> 96, scope["group"]
        if any(edge not in scope for edge in ("call", "raw", "lc")):
            incomplete += 1
            continue
        windows = union(m_windows[key])
        intervals, no_m_exec = cycle_breakdown(spans[key], windows, scope["call"], scope["raw"])
        uncovered = interval_cycles(scope["call"], scope["raw"]) - sum(intervals.values())
        if not 0 <= uncovered <= 4:
            raise ValueError("controller trace does not cover scope {}".format(key))
        record_stats = records[key]
        if group < 58:
            # Full stripes are 192 columns. The last stripe splits 64 columns as 3/3/2 groups of 8.
            expected = ((2 if p == 2 else 3) * 16) if group == 57 else 128
            if any(record_stats[kind] != expected for kind in ("gate", "up")) or record_stats["down"]:
                raise ValueError("unexpected Gate/Up record coverage {}".format((key, group, record_stats)))
        else:
            # A Down group scans 86 K128 tiles for each assigned group of 8 columns.
            expected = 1376 if group != 63 else (516 if p == 0 else 430)
            if record_stats["down"] != expected or record_stats["gate"] or record_stats["up"]:
                raise ValueError("unexpected Down record coverage {}".format((key, group, record_stats)))
        if p in groups[(page, group)]:
            raise ValueError("duplicate FFN P group")
        m_exec_cycles = sum(interval_cycles(a, b) for a, b in windows)
        groups[(page, group)][p] = {
            **scope, "states": dict(intervals, outside_lc_state=uncovered),
            "states_without_m_exec": no_m_exec, "m_exec_cycles": m_exec_cycles,
            "records": record_stats, "owner": owner,
        }

    stats = defaultdict(lambda: {"latest_lc": Counter(), "latest_raw": Counter(),
                                 "last_lc_states": Counter(), "last_lc_scope_cycles": [],
                                 "last_lc_states_without_m_exec": Counter(), "raw_tail_states": Counter(),
                                 "last_lc_minus_first_lc": [], "raw_to_lc_of_last_lc": [],
                                 "last_lc_to_wait": [], "first_call_to_wait": [], "last_lc_m_exec_cycles": []})
    by_page = defaultdict(list)
    for (page, group), lanes in sorted(groups.items()):
        if sorted(lanes) != [0, 1, 2]:
            continue
        if group >= len(waits[page]):
            incomplete += 1
            continue
        last_lc = max(lane["lc"] for lane in lanes.values())
        last_raw = max(lane["raw"] for lane in lanes.values())
        lc_targets = [p for p, lane in lanes.items() if lane["lc"] == last_lc]
        raw_targets = [p for p, lane in lanes.items() if lane["raw"] == last_raw]
        kind = "gate_up" if group < 58 else "down"
        summary = stats[kind]
        summary["latest_lc"][",".join(map(str, lc_targets))] += 1
        summary["latest_raw"][",".join(map(str, raw_targets))] += 1
        target = max(lc_targets, key=lambda p: lanes[p]["raw"])
        critical = lanes[target]
        summary["last_lc_m_exec_cycles"].append(critical["m_exec_cycles"])
        summary["last_lc_states"].update(critical["states"])
        summary["last_lc_states_without_m_exec"].update(critical["states_without_m_exec"])
        second_raw = sorted(lane["raw"] for lane in lanes.values())[-2]
        raw_target = raw_targets[0]
        raw_key = (lanes[raw_target]["owner"], raw_target)
        tail, _ = cycle_breakdown(spans[raw_key], [], second_raw, last_raw)
        summary["raw_tail_states"].update(tail)
        summary["last_lc_scope_cycles"].append(interval_cycles(critical["call"], critical["raw"]))
        summary["last_lc_minus_first_lc"].append(interval_cycles(min(lane["lc"] for lane in lanes.values()), last_lc))
        summary["raw_to_lc_of_last_lc"].append(interval_cycles(critical["raw"], last_lc))
        _, when = waits[page][group]
        calls = min(lane["call"] for lane in lanes.values())
        if group and calls <= waits[page][group - 1][1]:
            raise ValueError("next FFN wave launched before previous WAIT")
        details = dict(first_call_to_wait=interval_cycles(calls, when),
                       last_lc_to_wait=interval_cycles(last_lc, when),
                       latest_raw=raw_targets, latest_lc=lc_targets, lanes=lanes)
        summary["last_lc_to_wait"].append(details["last_lc_to_wait"])
        summary["first_call_to_wait"].append(details["first_call_to_wait"])
        by_page[page].append((group, details))

    pages = {}
    for page, page_groups in by_page.items():
        pcs = {pc for pc, _ in waits[page]}
        if len(pcs) != 1:
            raise ValueError("changed FFN WAIT instruction in page {}".format(page))
        pages[page] = dict(wait_pc=pcs.pop(), groups=len(page_groups), waits=len(waits[page]),
                           wave_details=dict(page_groups))
    if not partial and (pending != (0, 0, 0) or incomplete or len(pages) != 2 or
                        len(groups) != 128 or len(scopes) != 384 or set(waits) != set(pages) or
                        any(page["groups"] != 64 or page["waits"] != 64 for page in pages.values())):
        raise ValueError("incomplete FFN pages, scopes or records")
    for kind in stats:
        for name, values in stats[kind].items():
            if isinstance(values, list):
                stats[kind][name] = {"sum": sum(values), "median": median(values), "max": max(values)}
    return dict(trace_sha256=digest, partial=partial, scopes=len(scopes),
                incomplete_scopes=incomplete, pages=pages, phases=stats)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("assets", type=Path)
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    result = report(args.trace, args.assets, args.partial)
    if args.summary:
        for page in result["pages"].values():
            del page["wave_details"]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
