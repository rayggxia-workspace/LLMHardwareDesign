"""Independent small-path enumeration and malformed-input refusal checks."""
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import tempfile

from analyse import HERE, checked_json, decode_capacity, longest, sha, topology


def enumerate_paths(nodes, factors):
    # Enumerate all root-to-vertex paths, without a dynamic-programming table.
    def paths(i):
        cost = math.ceil(Fraction(nodes[i]['duration']) * factors.get(nodes[i]['op'], 1))
        if not nodes[i]['parents']:
            return [cost]
        return [cost + total for p in nodes[i]['parents'] for total in paths(p)]
    return max(value for i in range(len(nodes)) for value in paths(i))


def main():
    checked = 0
    rng = random.Random(244)
    for _ in range(300):
        nodes = []
        for i in range(rng.randint(2, 8)):
            nodes.append(dict(op=rng.choice(['Dot', 'Add', 'Product', 'Other']),
                              duration=rng.randrange(0, 101),
                              parents=[j for j in range(i) if rng.random() < .35]))
        for factors in ({}, {'Dot': Fraction(1, 2)}, {'Add': 0, 'Product': Fraction(2, 3)}):
            assert longest(nodes, factors)['ticks'] == enumerate_paths(nodes, factors)
            checked += 1
    # The old critical chain can cease to be critical after contraction.
    fork = [dict(op='Dot', duration=100, parents=[]),
            dict(op='Add', duration=90, parents=[]),
            dict(op='Other', duration=0, parents=[0, 1])]
    assert longest(fork)['ticks'] == 100
    assert longest(fork, {'Dot': Fraction(1, 2)})['ticks'] == 90
    rejected = 0
    for bad in ([dict(op='Dot', duration=1, parents=[1]), dict(op='Add', duration=1, parents=[0])],
                [dict(op='Dot', duration=1, parents=[0])],
                [dict(op='Dot', duration=1, parents=[5])],
                [dict(op='Dot', duration=1, parents=[]), dict(op='Add', duration=1, parents=[0, 0])]):
        try:
            topology(bad)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('malformed graph accepted')
    # The desktop sandbox's default TEMP may be read-only. Use an owned file.
    with tempfile.NamedTemporaryFile(dir=HERE, suffix='.json', delete=False) as stream:
        p = Path(stream.name)
    try:
        p.write_text('{"value":1}')
        original = sha(p)
        assert checked_json(p, original)['value'] == 1
        p.write_text('{"value":2}')
        try:
            checked_json(p, original)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('changed source accepted')
    finally:
        p.unlink()
    spec = json.loads((HERE/'study.json').read_text())
    config = checked_json(HERE/'qwen2.5-3b-config.json', spec['config_sha256'])
    capacity = decode_capacity(config, spec)
    matrix_products = 36*(4194304 + 524288 + 524288 + 4194304 + 3*22544384) + 311164928
    assert matrix_products == capacity['dense_linear_macs_per_token'] == 3085697024
    assert capacity['ceilings'][0]['optimistic_linear_token_s_ceiling'] < 5
    assert capacity['ceilings'][1]['optimistic_linear_token_s_ceiling'] > 10
    assert capacity['ceilings'][3]['optimistic_linear_token_s_ceiling'] < 2
    assert capacity['kv'][1]['s16_kv_read_bytes_ideal_gqa_reuse'] == 18874368
    print(json.dumps(dict(passed=True, independently_enumerated_dag_cases=checked,
                          critical_path_switch_checked=True, malformed_or_mutated_inputs_rejected=rejected,
                          dense_shape_crosscheck=True, precision_distinction=True)))


if __name__ == '__main__':
    main()
