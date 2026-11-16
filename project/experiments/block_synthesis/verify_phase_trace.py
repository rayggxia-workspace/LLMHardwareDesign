"""Compare every SystemC phase timestamp against the integer event oracle."""
import argparse
import json
from pathlib import Path


def verify(reference, logs):
    result = {}
    for mode, log in logs.items():
        actual = [tuple(map(int, line.split()[1:])) for line in log.splitlines() if line.startswith('PHASE ')]
        final = [int(line.split()[1]) for line in log.splitlines() if line.startswith('PHASE_COMPLETE ')]
        expected = reference[mode]
        if actual != [tuple(row) for row in expected['rows']] or final != [expected['makespan']]:
            raise ValueError('SystemC phase trace mismatch: ' + mode)
        result[mode] = {'makespan_ticks': final[0], 'checked_phases': len(actual)}
    return {'passed': True, 'modes': result,
            'scope': 'bounded timing-only native-command phase probe; independent integer event oracle',
            'unqualified': 'RTL arbitration/CDC, actual addresses, data values, energy, full model, physical clock and token/s'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reference', type=Path)
    parser.add_argument('whole', type=Path)
    parser.add_argument('phased', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = verify(json.loads(args.reference.read_text()), {
        'whole-service': args.whole.read_text(), 'descriptor-phases': args.phased.read_text()})
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
