"""Compare C639 FFN scope and mother WAIT timing for the same two invocations."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median


def matched_waves(base, trial):
    for page, timing in base["pages"].items():
        if page not in trial["pages"]:
            continue
        other = trial["pages"][page]
        if timing["wait_pc"] != other["wait_pc"]:
            raise ValueError("mother WAIT instruction differs by variant")
        for index, wave in timing["wave_details"].items():
            if index not in other["wave_details"]:
                continue
            after = other["wave_details"][index]
            kind = "gate_up" if int(index) < 58 else "down"
            fields = ("gate", "up", "down")
            for p, lane in wave["lanes"].items():
                b = after["lanes"][p]
                if lane["owner"] != b["owner"] or any(
                    lane["records"].get(k, 0) != b["records"].get(k, 0) for k in fields
                ):
                    raise ValueError("record identity differs for page {} wave {} P{}".format(page, index, p))
            yield page, index, kind, wave, after


def compare(base, trial):
    delta = defaultdict(list)
    p_states = defaultdict(lambda: [Counter(), Counter()])
    pages = defaultdict(dict)
    for page, index, phase, before, after in matched_waves(base, trial):
        wait = before["first_call_to_wait"], after["first_call_to_wait"]
        delta[phase].append(wait)
        pages[page][index] = dict(baseline_cycles=wait[0], candidate_cycles=wait[1])
        for key, row in enumerate((before, after)):
            lane = max((row["lanes"][str(i)] for i in row["latest_lc"]), key=lambda v: v["raw"])
            p_states[phase][key].update(lane["states_without_m_exec"])

    if not base["partial"] and not trial["partial"] and sorted(map(len, pages.values())) != [64, 64]:
        raise ValueError("two complete runs must match two 64-wave FFN pages")
    summary = {}
    for phase, timings in delta.items():
        before, after = [sum(values) for values in zip(*timings)]
        summary[phase] = dict(
            waves=len(timings), baseline_cycles=before, candidate_cycles=after,
            candidate_change_pct=100 * (after - before) / before,
            improved=sum(b > a for b, a in timings), ties=sum(b == a for b, a in timings),
            median_change_cycles=median(a - b for b, a in timings),
            baseline_last_lane_states_without_m_exec=p_states[phase][0],
            candidate_last_lane_states_without_m_exec=p_states[phase][1],
        )
    return dict(
        baseline_sha256=base["trace_sha256"], candidate_sha256=trial["trace_sha256"],
        partial=base["partial"] or trial["partial"], summary=summary, waves_by_page=pages,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    a, b = (json.loads(p.read_bytes()) for p in (args.baseline, args.candidate))
    print(json.dumps(compare(a, b), indent=2))


if __name__ == "__main__":
    main()
