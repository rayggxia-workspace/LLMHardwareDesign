"""Compare state-dependent SRAM replay against the #251 RTL probe logs."""
import argparse
import json
from pathlib import Path

from event_replay import Operation, Phase, replay


# Each pair is (requests, first tick at which the downstream takes responses).
CASES = (
    ((3, 0), (0, 0)),
    ((3, 0), (3, 0)),
    ((3, 0), (3, 6)),
    ((3, 9), (3, 6)),
    ((3, 0), (1, 0)),
    ((7, 0), (0, 0)),
    ((3, 0), (1, 9)),
    ((7, 0), (0, 9)),
)
CAPACITY = {'port': 1, 'narrow.response': 2, 'wide.response': 2, 'narrow.pop': 1, 'wide.pop': 1}


def predict(mode):
    ports = ('narrow', 'wide')
    gates = tuple(Operation((Phase('take opens', unstall - 1),))
                  for _, unstall in CASES[mode] if unstall)
    next_gate = 0
    requests = {}
    for port, (count, unstall) in zip(ports, CASES[mode]):
        # ACK completion is the sampled handshake. This one-cycle phase
        # serializes pops and releases the reservation at that same edge.
        after = (frozenset(), frozenset({(next_gate, 0)})) if unstall else ()
        next_gate += bool(unstall)
        for index in range(count):
            requests[port, index] = Operation(
                (Phase('issue', 1, (('port', 1),), priority=-int(port == 'wide')),
                 Phase('ack', 1, ((f'{port}.pop', 1),))),
                holds=((f'{port}.response', 1),), phase_after=after)

    operations = gates + tuple(requests.values())
    results = replay(operations, CAPACITY)
    if len(requests) > 3:
        old = replay(operations[:len(gates) + 3], CAPACITY)
        if replay(operations, CAPACITY, previous=old) != results:
            raise ValueError(f'mode {mode} incremental replay differs from reset replay')
    return {(port, index, event): tick
            for (port, index), (issue, ack) in zip(requests, results[len(gates):])
            for event, tick in (('issue', issue.start), ('ack', ack.end))}


def check_trace(mode, lines):
    observed = {}
    passes = []
    for line in lines:
        if line.startswith('PASS '):
            passes.append(line.strip())
        if line.startswith('TRACE '):
            _, port, index, event, tick = line.split()
            key = port, int(index), event
            if key in observed:
                raise ValueError(f'mode {mode} duplicate handshake {key}')
            observed[key] = int(tick)
    if passes != [f'PASS mode={mode}']:
        raise ValueError(f'mode {mode} missing unique RTL PASS')
    expected = predict(mode)
    for key in sorted(observed.keys() | expected.keys()):
        if observed.get(key) != expected.get(key):
            raise ValueError(f'mode {mode} {key}: RTL={observed.get(key)}, replay={expected.get(key)}')
    return {'handshakes': len(observed), 'end': max(observed.values()),
            'old_first_issue': observed['narrow', 0, 'issue'],
            'old_last_ack': observed['narrow', 2, 'ack']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log_dir', type=Path, help='directory containing native-sram-mode-*.log')
    args = parser.parse_args()
    outcomes = []
    for mode in range(len(CASES)):
        with (args.log_dir / f'native-sram-mode-{mode}.log').open(encoding='utf-8') as source:
            outcomes.append(check_trace(mode, source))
    print(json.dumps(outcomes, indent=2))


if __name__ == '__main__':
    main()
