"""Frozen Issue153 engineering gates; these are not general model-quality metrics.

Return 0 only for a numerical pass, 1 for an observed failure. Invalid input is an
error, not a passing or failing experiment. Read independent validation.json only;
this script never supplies predictions to the SystemC runtime.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

GATES = {'logits_cosine_min': .999, 'logits_relative_l2_max': .05,
         'hidden_cosine_min': .995, 'hidden_relative_l2_max': .10,
         'all_same_prefix_top1': True, 'independent_greedy_equal': True}


def assess(path):
    raw = path.read_bytes()
    result = json.loads(raw)
    steps = result['steps']
    if not steps:
        raise ValueError('empty validation')
    failures = []
    for step in steps:
        if not step['hidden']:
            raise ValueError('missing hidden boundaries')
        if not step['top1_equal']:
            failures.append({'step': step['step'], 'kind': 'top1'})
        for kind, rows in [('logits', [step['logits']]), ('hidden', step['hidden'])]:
            for boundary, row in enumerate(rows):
                cosine, relative = row['cosine'], row['relative_l2']
                if not all(math.isfinite(x) for x in (cosine, relative)):
                    raise ValueError('nonfinite metric')
                if cosine < GATES[kind+'_cosine_min'] or relative > GATES[kind+'_relative_l2_max']:
                    failures.append({'step': step['step'], 'kind': kind,
                                     'boundary': boundary, 'metrics': row})
    greedy = result['systemc_generated'] == result['independent_greedy_reference_generated']
    if not greedy:
        failures.append({'kind': 'independent_greedy'})
    return {'scope': 'short text execution; no general quality, long-context or hardware performance claim',
            'validation_sha256': hashlib.sha256(raw).hexdigest(), 'gates': GATES,
            'accepted': not failures, 'steps': len(steps),
            'top1_equal': sum(s['top1_equal'] for s in steps), 'greedy_equal': greedy,
            'worst_logits_cosine': min(s['logits']['cosine'] for s in steps),
            'worst_logits_relative_l2': max(s['logits']['relative_l2'] for s in steps),
            'worst_hidden_cosine': min(h['cosine'] for s in steps for h in s['hidden']),
            'worst_hidden_relative_l2': max(h['relative_l2'] for s in steps for h in s['hidden']),
            'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('validation', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    report = assess(args.validation)
    text = json.dumps(report, indent=2, ensure_ascii=False)+'\n'
    if args.out:
        with args.out.open('x', encoding='utf-8') as f:
            f.write(text)
    print(text)
    raise SystemExit(0 if report['accepted'] else 1)


if __name__ == '__main__':
    main()
