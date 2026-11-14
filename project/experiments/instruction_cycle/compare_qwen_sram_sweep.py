"""Compare independently executed Qwen bandwidth cases with their archived TLM runs."""

import argparse
from itertools import zip_longest
import json
from pathlib import Path


def load_case(mode, directory):
    result = json.loads((directory / "execution.json").read_bytes())
    audit = json.loads((directory / "timing-audit.json").read_bytes())
    with (directory / "page-timing.jsonl").open(encoding="ascii") as stream:
        pages = [json.loads(row) for row in stream]
    count = 582 if mode == "decode" else 578
    if len(pages) != count or result["pages"] != count:
        raise ValueError(f"{directory} does not have all {count} pages")
    if mode == "decode":
        first, second = result["retirements"]
        elapsed = second[1] - first[1]
        ends = [pages[290]["end_ps"], pages[-1]["end_ps"]]
        if (ends != [first[1], second[1]] or elapsed != result["retirement_interval_ps"] or
                audit["retirement_ps"] != ends):
            raise ValueError(f"{directory} retirement timing fails to reconcile")
        tokens = 1
    else:
        elapsed = pages[-1]["end_ps"] - pages[0]["start_ps"]
        tokens = 2
    if elapsed <= 0 or result["ddr"]["reads"] + result["ddr"]["writes"] != result["ddr"]["callbacks"]:
        raise ValueError(f"{directory} timing or DDR drain does not reconcile")
    return result, audit, pages, elapsed, tokens


def signed_error(candidate, reference):
    return 100.0 * (candidate - reference) / reference


def compare(mode, reference, candidate):
    old, old_audit, old_pages, old_elapsed, tokens = load_case(mode, reference)
    new, new_audit, new_pages, new_elapsed, _ = load_case(mode, candidate)
    diffs = []
    max_page_duration_error = 0
    for index, (left, right) in enumerate(zip_longest(old_pages, new_pages), 1):
        if left != right:
            fields = sorted(k for k in left.keys() | right.keys() if left.get(k) != right.get(k))
            diffs.append({"row": index, "step": left["step"], "page": left["page"], "fields": fields})
        left_elapsed = left["end_ps"] - left["start_ps"]
        right_elapsed = right["end_ps"] - right["start_ps"]
        max_page_duration_error = max(max_page_duration_error, abs(left_elapsed - right_elapsed))
    old_tps, new_tps = tokens * 1e12 / old_elapsed, tokens * 1e12 / new_elapsed
    return {"mode": mode, "reference_elapsed_ps": old_elapsed, "candidate_elapsed_ps": new_elapsed,
            "elapsed_error_ps": new_elapsed - old_elapsed,
            "signed_elapsed_error_percent": signed_error(new_elapsed, old_elapsed),
            "reference_tok_s": old_tps, "candidate_tok_s": new_tps,
            "signed_throughput_error_percent": signed_error(new_tps, old_tps),
            "pages": len(old_pages), "exact_pages": len(old_pages) - len(diffs),
            "max_absolute_page_duration_error_ps": max_page_duration_error,
            "first_difference": diffs[0] if diffs else None,
            "execution_equal": old == new, "timing_audit_equal": old_audit == new_audit,
            "reference_ddr": old["ddr"], "candidate_ddr": new["ddr"],
            "reference_retirements": old.get("retirements"), "candidate_retirements": new.get("retirements")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("decode", "prefill"))
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.mode, args.reference, args.candidate), indent=2))


if __name__ == "__main__":
    main()
