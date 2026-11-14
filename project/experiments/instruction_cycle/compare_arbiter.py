"""Compare every handshake against the independent directed RTL testbench."""

import argparse
import json
from pathlib import Path

from s_arbiter import Request, simulate


def scenario(case):
    if case == 0:
        arrivals = ((0, 0, 8), (0, 0, 4), (0, 0, 5))
        memory = ((1, 3), (16, 18))
        receivers = (((6, 8),), ((12, 14),), ())
    else:
        arrivals = ((2, 2, 14), (0, 0, 0), (0, 1, 13))
        memory = ((1, 2), (19, 22))
        receivers = ((), ((5, 7),), ((12, 14),))
    requests = [[Request(at, index, 4 if index % 2 == 0 else 12 + client, (client + index) % 2)
                 for index, at in enumerate(stream)] for client, stream in enumerate(arrivals)]
    events = simulate(requests, memory, receivers, response_latency=2)
    events.append({"event": "summary", "case": case, "cycle": events[-1]["cycle"],
                   "grants": 9, "sends": 9, "responses": 9})
    return events


def compare(directory):
    result = []
    for case in (0, 1):
        path = directory / "rtl-{}.log".format(case)
        lines = path.read_text(encoding="utf-8").splitlines()
        if any("%Error" in line or "%Fatal" in line or "** Fatal" in line for line in lines):
            raise ValueError("RTL failed: " + str(path))
        observed = []
        for line in lines:
            if line.startswith("# "):  # ModelSim transcript prefix
                line = line[2:]
            if line.startswith("{"):
                observed.append(json.loads(line))
        predicted = scenario(case)
        if len(observed) != len(predicted):
            raise ValueError("case {}: expected {} records, got {}".format(case, len(predicted), len(observed)))
        for index, (expected, actual) in enumerate(zip(predicted, observed)):
            if expected != actual:
                raise ValueError("case {} record {}: predicted {}, RTL {}".format(case, index, expected, actual))
        result.append({"case": case, "matched_handshakes": len(predicted) - 1,
                       "last_response_cycle": predicted[-1]["cycle"], "max_cycle_error": 0})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rtl_logs", type=Path)
    print(json.dumps(compare(parser.parse_args().rtl_logs), indent=2))
