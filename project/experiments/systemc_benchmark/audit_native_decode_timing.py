"""Reconcile two instruction-driven retirements with the executed page timeline."""

import argparse
from collections import Counter
import json
from pathlib import Path


def audit(run):
    result = json.loads((run / "execution.json").read_bytes())
    retirements = [time for _, time in result["retirements"]]
    if (result["initial_history"], result["positions"], result["kv_cross_step_read_beats"],
            len(retirements)) != (512, 514, 1152, 2):
        raise ValueError("incomplete two-step native decode")
    totals = [Counter(), Counter()]
    counts = [0, 0]
    ends = [0, 0]
    last = 0
    with (run / "page-timing.jsonl").open(encoding="ascii") as stream:
        for raw in stream:
            row = json.loads(raw)
            step = row["step"] - 1
            start, ingress, pm, dispatch, end = (row[k] for k in
                ("start_ps", "ingress_end_ps", "pm_end_ps", "dispatch_start_ps", "end_ps"))
            if (step not in (0, 1) or row["page"] != counts[step]
                    or not last == start <= ingress <= pm <= dispatch <= end):
                raise ValueError("discontinuous page schedule")
            counts[step] += 1
            last = ends[step] = end
            instructions = row["mother_instruction_cycles"] * 3334
            wait = row["mother_wait_ps"]
            barrier = row["mid_barrier_ps"]
            remainder = end - dispatch - instructions - wait - barrier
            if min(instructions, wait, barrier, remainder) < 0:
                raise ValueError("page wall-time categories overlap")
            totals[step].update(ingress_ps=ingress-start, program_load_ps=pm-ingress,
                                pre_dispatch_ps=dispatch-pm, mother_instruction_ps=instructions,
                                mother_wait_ps=wait, ffn_barrier_ps=barrier, other_dispatch_ps=remainder,
                                elapsed_ps=end-start)
            totals[step].update(sram_port_wait_ps=row["sram_port_wait_ps"],
                                ddr_queue_ps=row["ddr"].get("ddr_queue_ps", 0),
                                ddr_inflight_ps=row["ddr"].get("ddr_inflight_ps", 0))
    interval = retirements[1] - retirements[0]
    if (ends != retirements or counts[0] == 0 or counts[1] == 0 or interval <= 0 or
            interval != result["retirement_interval_ps"]):
        raise ValueError("retirement timestamps do not match page completion")
    return dict(scope=result["scope"], timing_calibrated=result["timing_calibrated"],
                retirement_ps=retirements, interval_tok_s=1e12 / interval,
                pages_per_step=counts, timing_by_step_ps=totals,
                overlapping_counters=["sram_port_wait_ps", "ddr_queue_ps", "ddr_inflight_ps"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.run), indent=2))
