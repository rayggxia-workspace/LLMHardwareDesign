"""Check captured RMS fixed-point outputs; this does not certify RTL or FP32 error."""
import argparse
from math import isqrt
import json
from pathlib import Path


def rounded(value, shift):
    if shift <= 0:
        return value << -shift
    q, r = divmod(value, 1 << shift)
    return q + int(r * 2 > (1 << shift) or (r * 2 == (1 << shift) and q % 2))


def verify(path):
    data = json.loads(path.read_text())
    if not data['n_counts_reconciled'] or not data['samples']:
        raise ValueError('missing reconciled samples')
    for sample in data['samples']:
        values = sample['source']
        extra = 0
        while any(not -32768 <= rounded(x << sample['shift'], extra) <= 32767 for x in values):
            extra += 1
        squares = sum(rounded(x << sample['shift'], extra) ** 2 for x in values)
        eps = max(1, rounded(sample['epsilon'], 2 * extra))
        denominator = isqrt((squares << 14) // sample['words'] + (eps << 16))
        raw = (1 << 38) // denominator
        factor = raw if sample['shifted_format'] else rounded(raw, extra)
        intermediate_shift = 13 + extra if sample['shifted_format'] else 13
        expected = [rounded(rounded((x << sample['shift']) * factor, intermediate_shift) * g,
                            17 + sample['output_shift']) for x, g in zip(values, sample['gamma'])]
        if (extra, factor, expected) != (sample['extra'], sample['factor'], sample['expected']):
            raise ValueError('captured arithmetic mismatch: ' + sample['signature'])
    summary = dict(passed=True, samples=len(data['samples']),
                   rms_services=sum(data['rms_service_counts'].values()),
                   scope='captured fixed-point RMS inputs/factors/results; RTL and FP32 accuracy pending')
    path.with_name('arithmetic-capture-check.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    verify(parser.parse_args().capture)
