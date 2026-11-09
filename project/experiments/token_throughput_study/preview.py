"""Reproduce small arithmetic bounds without loading the full 707 MiB graph."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import platform

from analyse import HERE, checked_json, decode_capacity, descriptor_sweep, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('use a fresh output file')
    spec = json.loads((HERE/'study.json').read_text())
    config = checked_json(HERE/'qwen2.5-3b-config.json', spec['config_sha256'])
    # PR241 DIAGNOSIS.md attributes this chain to the greedy plan, not the DP.
    chain = dict(Dot=84500059460, Product=34877867696, Add=33740886712, Other=14292059254)
    total = sum(chain.values())
    assert total == 167410873122
    scenarios = [('dot_half', {'Dot': Fraction(1, 2)}),
                 ('pointwise_half', {'Product': Fraction(1, 2), 'Add': Fraction(1, 2)}),
                 ('both_half', dict.fromkeys(('Dot', 'Product', 'Add'), Fraction(1, 2))),
                 ('add_ffn_ratio_hypothesis', {'Add': Fraction(632654644, 901467136)})]
    bounds = []
    for name, factors in scenarios:
        surviving = sum(Fraction(value)*factors.get(op, 1) for op, value in chain.items())
        assert surviving > 0
        # Every original path remains in the fixed DAG. A different chain can
        # dominate, so this is a speedup ceiling, never an achievable speedup.
        cap = Fraction(total, 1)/surviving
        bounds.append(dict(name=name, factors={k: str(v) for k, v in factors.items()},
                           surviving_old_chain_ticks_lower_bound=float(surviving),
                           fixed_graph_speedup_upper_bound=float(cap),
                           exact_speedup_bound=[cap.numerator, cap.denominator]))
    result = dict(kind='local configuration arithmetic and old-chain necessary bounds; no full-graph execution',
                  source_pr241_commit=spec['pr241_commit'], greedy_chain=chain, greedy_chain_ticks=total,
                  dp_plan_ticks=spec['plan_ticks'], chain_sensitivity_upper_bounds=bounds,
                  decode=decode_capacity(config, spec), descriptor=descriptor_sweep(),
                  python=platform.python_version(),
                  source_sha256={name: sha(HERE/name) for name in (
                      'analyse.py', 'preview.py', 'study.json', 'qwen2.5-3b-config.json')},
                  scope='whole-service hypothetical factors; not calibrated token/s or demonstrated improvement')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(output=str(args.out), sha256=sha(args.out), bounds=bounds)))


if __name__ == '__main__':
    main()
