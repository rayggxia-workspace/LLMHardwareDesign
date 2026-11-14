"""Run and audit the early-stop 105530 projection probe."""

import argparse
import hashlib
import json
from pathlib import Path

from instrument_qwen_105530 import CORE_PERIOD_PS, FIRST_EDGE_PS, replace_once, verify


PREFIX_EVENTS = 1292  # startup through the two completed weight records
COPY_EVENTS = {
    "copy_read": "copy_reads",
    "copy_write": "copy_writes",
    "copy_ack": "copy_acks",
    "a_load_read": "a_load_reads",
    "a_load_ack": "a_load_acks",
    "weight_fill_ack": "weight_fill_ack",
}
EXEC_EVENTS = (
    "guard_accept", "exec_first_flit", "exec_last_flit", "a_use", "m_exec_start",
    "first_operand", "last_operand", "raw_accept", "input_eop", "rf_eop",
)


def prepare_runner(path):
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, '"${runtime[@]}" \\\n', '"${runtime[@]}" "+QWEN_K0_STOP" \\\n')
    start = text.index(" grep -E '^(PASS q projection")
    end = text.index("\n}\n", start)
    text = text[:start] + ' grep -q "^QWEN_K0_STOP " "$case_dir/replay-$mode.log"' + text[end:]
    # Run both unchanged native modes, then stop before the full-window audits.
    end = text.index('\npython3 "$EXP/audit_native_projection_replay.py"')
    path.write_bytes((text[:end] + "\n").encode("utf-8"))


def expected_cycles(prediction):
    pair = prediction["projection_pair"]
    expected = {event: pair[key] for event, key in COPY_EVENTS.items()}
    expected["a_load_proof"] = [pair["a_load_proof"]]
    expected["third_weight_accept"] = [pair["third_weight_source_offer"]]
    expected.update({event: [record[event] for record in pair["exec"]] for event in EXEC_EVENTS})
    return expected


def read_probe(path):
    events = {}
    stop_count = 0
    previous = -1
    with path.open(encoding="utf-8") as log:
        for line in log:
            if line.startswith("QWEN_K0_STOP "):
                stop_count += 1
            if not line.startswith("QWEN_K0 "):
                continue
            _, kind, *fields = line.split()
            row = {key: int(value) for key, value in (field.split("=") for field in fields)}
            cycle = row.pop("cycle") - 1
            verify(cycle >= 0 and row.pop("ps") == FIRST_EDGE_PS + CORE_PERIOD_PS * cycle,
                   "invalid probe core clock")
            verify(cycle >= previous, "nonmonotone probe clock")
            previous = cycle
            events.setdefault(kind, []).append({"cycle": cycle, **row})
    verify(stop_count == 1, "expected one third-weight stop")
    return events


def verify_ddr_prefix(replay, baseline, mode):
    name = Path("DDR-{}".format(mode)) / "transactions.tsv"
    with (replay / name).open("rb") as actual, (baseline / name).open("rb") as reference:
        for index in range(PREFIX_EVENTS):
            row = actual.readline()
            verify(row and row == reference.readline(), "probe changed frozen DDR event {}".format(index))
        verify(not actual.readline(), "probe ran beyond the third source admission")


def compare(predictions, replay, baseline):
    result = []
    for mode in (0, 1):
        path = predictions / ("prediction-{}.json".format(mode))
        data = path.read_bytes()
        prediction = json.loads(data)
        verify(prediction["mode"] == mode, "prediction mode differs")
        events = read_probe(replay / ("replay-{}.log".format(mode)))
        verify_ddr_prefix(replay, baseline, mode)
        expected = expected_cycles(prediction)
        actual = {event: [row["cycle"] for row in events.get(event, [])] for event in expected}
        differences = {event: {"expected": expected[event], "actual": actual[event]}
                       for event in expected if actual[event] != expected[event]}
        result.append({"mode": mode, "prediction_sha256": hashlib.sha256(data).hexdigest(),
                       "matched_original_ddr_events": PREFIX_EVENTS,
                       "matched_internal_edges": sum(len(actual[event]) for event in expected
                                                     if event not in differences),
                       "differences": differences, "observed": events})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    prepare = commands.add_parser("prepare-runner")
    prepare.add_argument("runner", type=Path)
    check = commands.add_parser("compare")
    for name in ("predictions", "replay", "baseline"):
        check.add_argument(name, type=Path)
    accept = commands.add_parser("require-match")
    accept.add_argument("audit", type=Path)
    args = parser.parse_args()
    if args.command is None:
        parser.error("a command is required")
    if args.command == "prepare-runner":
        prepare_runner(args.runner)
    elif args.command == "compare":
        print(json.dumps(compare(args.predictions, args.replay, args.baseline), indent=2))
    else:
        rows = json.loads(args.audit.read_bytes())
        verify(all(not mode["differences"] for mode in rows), "projection probe differs from prediction")


if __name__ == "__main__":
    main()
