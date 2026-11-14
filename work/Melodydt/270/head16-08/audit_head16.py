"""Audit sealed two-step decode, short prefill, and native vocabulary timings."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re

TILES = 1187
READS = 5472454
CORE_PS = 3334


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines()]


def stable_page(row):
    sram = {name: {key: val for key, val in stats.items() if key != "port_wait_ps"}
            for name, stats in row["sram"].items()}
    return ([(*call["provider"], call["count"]) for call in row["calls"]],
            {key: row["ddr"].get(key, 0) for key in ("reads", "writes", "callbacks")}, sram)


def audit_decode(run):
    execution = json.loads((run / "execution.json").read_bytes())
    timing = json.loads((run / "timing-audit.json").read_bytes())
    pages = jsonl(run / "page-timing.jsonl")
    head = jsonl(run / "head16.jsonl")
    if (len(pages), len(head), execution["initial_history"], execution["positions"],
            execution["sram_port_bits"], execution["kv_cross_step_read_beats"],
            timing["pages_per_step"]) != (582, 2, 512, 514, 512, 1152, [291, 291]):
        raise ValueError("wrong two-step workflow or unproven cross-step KV")
    head_totals = []
    for step, record in enumerate(head, 1):
        page = pages[step * 291 - 1]
        if ((record["step"], record["page"], record["columns"]) != (step, page["page"], 151936)
                or record["retirement_ps"] != page["end_ps"]
                or [record["token"], record["retirement_ps"]] != execution["retirements"][step - 1]
                or not re.fullmatch(r"[0-9a-f]{64}", record["logits_sha256"])
                or len(record["tiles"]) != TILES):
            raise ValueError(f"incomplete HEAD16 retirement for step {step}")
        totals = Counter()
        prior = page["start_ps"]
        for index, tile in enumerate(record["tiles"]):
            begin, compute_end, read_end, end = [tile[key] for key in
                ("launch_ps", "m_terminal_ps", "read_done_ps", "argmax_done_ps")]
            if (not prior <= begin <= compute_end <= read_end <= end <= page["end_ps"]
                    or (tile["first"], tile["weight_beats"], tile["records"]) != (128 * index, 4608, 256)):
                raise ValueError(f"invalid HEAD16 tile {index} at step {step}")
            active = sum(tile[key] for key in ("activation_ps", "weight_wait_ps", "m_exec_ps", "write_ps"))
            remainder = compute_end - begin - active
            if remainder < 0:
                raise ValueError("HEAD16 stage time exceeds tile wall time")
            totals.update(activation_ps=tile["activation_ps"], weight_wait_ps=tile["weight_wait_ps"],
                          m_exec_ps=tile["m_exec_ps"], s_write_ps=tile["write_ps"],
                          s_read_ps=read_end-compute_end, argmax_ps=end-read_end,
                          tile_control_ps=remainder, page_control_ps=begin-prior)
            prior = end
        totals["page_control_ps"] += page["end_ps"] - prior
        if sum(totals.values()) != page["end_ps"] - page["start_ps"]:
            raise ValueError("HEAD16 page stages fail to reconcile")
        head_totals.append(dict(totals))
    return execution, pages, head, head_totals


def compare_decode(baseline, candidate):
    b, bp, bh, bt = audit_decode(baseline)
    c, cp, ch, ct = audit_decode(candidate)
    for key in ("kv_binding_sha256", "deployment_sha256", "scope"):
        if b[key] != c[key]:
            raise ValueError(f"fixed decode configuration differs: {key}")
    for base, cand in zip(bp, cp, strict=True):
        if (base["step"], base["page"], stable_page(base)) != (cand["step"], cand["page"], stable_page(cand)):
            raise ValueError(f"fixed page service or traffic differs at {base['step']}/{base['page']}")
    def identity(record):
        return [record[key] for key in ("token", "logit", "logits_sha256")]
    if [identity(r) for r in bh] != [identity(r) for r in ch]:
        raise ValueError("weight-fetch refactoring changed raw logits or token")
    base_down = jsonl(baseline / "ffn-down.sha256.jsonl")
    cand_down = jsonl(candidate / "ffn-down.sha256.jsonl")
    if len(base_down) != 72 or base_down != cand_down:
        raise ValueError("FFN down data differs")
    return dict(baseline_tok_s=1e12/b["retirement_interval_ps"],
                candidate_tok_s=1e12/c["retirement_interval_ps"],
                baseline_retirements=b["retirements"], candidate_retirements=c["retirements"],
                numeric=[identity(r) for r in ch], baseline_head=bt, candidate_head=ct)


def compare_prefill(baseline, candidate):
    b = json.loads((baseline / "timing-audit.json").read_bytes())
    c = json.loads((candidate / "timing-audit.json").read_bytes())
    if b["pages"] != 578 or c["pages"] != 578 or b["elapsed_ps"] != c["elapsed_ps"]:
        raise ValueError("HEAD16-only candidate unexpectedly changed short prefill")
    bp = jsonl(baseline / "page-timing.jsonl")
    cp = jsonl(candidate / "page-timing.jsonl")
    if bp != cp or jsonl(baseline / "ffn-down.sha256.jsonl") != jsonl(candidate / "ffn-down.sha256.jsonl"):
        raise ValueError("short prefill page or FFN down data differs")
    return c


def native(run):
    files = list(run.glob("replay-*.log"))
    if len(files) != 1:
        raise ValueError(f"expected one product replay in {run}")
    log = files[0].read_text()
    full = re.findall(r"^PASS head projection tiles=1187 output_words=37984 DDR_reads=(\d+) cycles=(\d+) mode=(\d+)$", log, re.M)
    argmax = re.findall(r"^HEAD_ARGMAX (\d+)$", log, re.M)
    rows = [tuple(map(int, line.split()[1:])) for line in log.splitlines()
            if line.startswith("HEAD_TIMING ") and len(line.split()) == 11]
    if len(full) != 1 or len(argmax) != 1 or len(rows) != TILES:
        raise ValueError("missing native timed product evidence")
    requests, cycles, mode = map(int, full[0])
    if requests != READS:
        raise ValueError("unexpected native DDR request count")
    audit = json.loads((run / "vocabulary-audit.json").read_bytes())
    proof = audit["index_handoff"][str(mode)]
    sums = Counter()
    last = rows[0][1]
    for idx, (tile, begin, projection, read, end, m, weight, act, both, peak) in enumerate(rows, 1):
        other = projection - begin - m - weight - act - both
        if tile != idx or not last <= begin <= projection <= read <= end or other < 0 or peak != 4:
            raise ValueError(f"invalid native HEAD16 timing at tile {idx}")
        sums.update(between_tiles=begin-last, m_busy=m, weight_only=weight, activation_only=act,
                    activation_and_weight=both, other_projection=other, output_read=read-projection,
                    tile_terminal=end-read)
        last = end
    sums.update(final_argmax=int(argmax[0])-last, index_commit=proof["index_commit_cycle"]-int(argmax[0]),
                index_read=proof["index_read_cycle"]-proof["index_commit_cycle"])
    if min(sums.values()) < 0 or sum(sums.values()) != proof["index_read_cycle"] - rows[0][1]:
        raise ValueError("native breakdown does not reconcile")
    return dict(mode=mode, cycles=cycles, ddr_reads=requests, timing_cycles=dict(sums),
                numeric=audit["numeric"][str(mode)], index=proof)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="scope", required=True)
    for case in ("decode", "prefill", "native"):
        sub = subparsers.add_parser(case)
        sub.add_argument("baseline", type=Path)
        sub.add_argument("candidate", type=Path)
    args = parser.parse_args()
    if args.scope == "native":
        baseline, candidate = native(args.baseline), native(args.candidate)
        if (baseline["mode"], baseline["numeric"], baseline["ddr_reads"]) != (
                candidate["mode"], candidate["numeric"], candidate["ddr_reads"]):
            raise ValueError("native variant changed numeric result, traffic, or test mode")
        result = dict(baseline=baseline, candidate=candidate,
                      cycles_saved=baseline["cycles"]-candidate["cycles"])
    else:
        result = {"decode": compare_decode, "prefill": compare_prefill}[args.scope](
            args.baseline, args.candidate)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
