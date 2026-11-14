"""Read component Gather logs and verify the sequence required by the product audit."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from gather_index_evidence import EVENT_FIELDS, GatherIndexEvidence


def marker(line, names):
    name, *items = line.split()
    pairs = [item.split('=', 1) for item in items]
    if tuple(pair[0] for pair in pairs) != names or any(len(pair) != 2 for pair in pairs):
        raise ValueError(f'malformed {name}')
    return tuple(int(value) for _, value in pairs)


def verify(lines, *, step, page, generation, target, word, token):
    identity = step, page, generation
    checker = None
    terminal = None
    for line in lines:
        name, *_ = line.split()
        if terminal is not None:
            raise ValueError('event after Gather terminal')
        if name == 'NATIVE_GATHER_START':
            if checker is not None:
                raise ValueError('duplicate Gather start')
            *key, actual_token, cycle = marker(line, ('step', 'page', 'generation', 'token', 'cycle'))
            if tuple(key) != identity or token != actual_token:
                raise ValueError('Gather start differs from the phase binding')
            checker = GatherIndexEvidence(step=step, page=page, generation=generation, target=target,
                                          word=word, token=token, launch_cycle=cycle)
        elif checker is None:
            raise ValueError('Gather event precedes start')
        elif name == 'NATIVE_GATHER_TERMINAL':
            *key, status, cycle = marker(line, ('step', 'page', 'generation', 'status', 'cycle'))
            if tuple(key) != identity or status != 0:
                raise ValueError('wrong Gather terminal')
            terminal = dict(cycle=cycle, milestones=checker.finish(cycle))
        elif name in EVENT_FIELDS:
            checker.consume(line)
        else:
            raise ValueError('unknown Gather event')
    if terminal is None:
        raise ValueError('missing Gather terminal')
    return terminal


def negative_controls(lines, args):
    ack = next(i for i, row in enumerate(lines) if row.startswith('NATIVE_GATHER_INDEX_ACK '))
    read = next(i for i, row in enumerate(lines) if row.startswith('NATIVE_GATHER_INDEX_READ '))
    data = next(i for i, row in enumerate(lines) if row.startswith('NATIVE_GATHER_INDEX_DATA '))
    faults = {
        'missing_ack': lines[:ack] + lines[ack+1:],
        'duplicate_ack': lines[:ack] + [lines[ack]] + lines[ack:],
        'read_before_ack': lines[:ack] + [lines[read]] + lines[ack:read] + lines[read+1:],
        'wrong_sram_data': lines[:data] + [lines[data].replace(f'data={args["token"]<<64:032x}', 'data='+'0'*32)] + lines[data+1:],
        'stale_generation': lines[:ack] + [lines[ack].replace(f'generation={args["generation"]} ', 'generation=1 ')] + lines[ack+1:],
    }
    for fault, mutated in faults.items():
        if mutated == lines:
            raise ValueError(f'mutation did not apply: {fault}')
        try:
            verify(mutated, **args)
        except ValueError:
            continue
        raise ValueError(f'accepted invalid evidence: {fault}')
    return list(faults)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    for k in ('step', 'page', 'generation', 'target', 'word', 'token'):
        parser.add_argument(k, type=int)
    args = vars(parser.parse_args())
    log = args.pop('log').read_bytes()
    lines = [x for x in log.decode().splitlines() if x.startswith('NATIVE_GATHER_')]
    report = verify(lines, **args)
    report.update(identity=args, rejected=negative_controls(lines, args), log_sha256=sha256(log).hexdigest())
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
