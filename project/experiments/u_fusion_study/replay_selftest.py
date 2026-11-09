"""Small deterministic replay fixtures; no C++/RTL/server execution."""
from copy import deepcopy
import json

from fusion_contract import Op, Tensor, Trace, region_replay_contract, require
from replay import replay_region
from fusion_oracle import check_ownership, check_schedule, make_schedule, rejected


def fixture(length, fusion):
    tensors = tuple([Tensor(length, 32, True), Tensor(length, 32, True), Tensor(1, 32, True)] +
                    [Tensor(length, 32, False)] * 3)
    ops = (Op(3, 'Product', length, 1, length, 1, 1, 7, 1, (0, 1)),
           Op(4, 'Add', length, 1, length, 1, 1, 0, 1, (3, 2)),
           Op(5, 'Product', length, 1, length, 1, 1, 3, 0, (4, 1)))
    trace = Trace(tensors, ops, 1, 'synthetic')
    nodes = []
    for offset in range(0, length, 64):
        n = min(64, length - offset)
        for index, op in enumerate(ops):
            f_in = ops[index - 1].out if fusion and index else -1
            f_out = op.out if fusion and index < 2 else -1
            # A deliberately nonzero frozen memory latency, single controller.
            read = (1 if index == 1 else (n * 4 + 63) // 64) * 1000
            if f_in < 0:
                read += ((n * 4 + 63) // 64) * 1000
            inp = read + 17000
            out = 0 if f_out >= 0 else ((n * 4 + 63) // 64) * 1000 + 11000
            out_s = 0 if f_out >= 0 else ((n * 4 + 63) // 64) * 1000
            E = ((n + 3) // 4 + 5) * 1000
            nodes.append([len(nodes) + 1, 1, index, offset, n, f_in, f_out,
                          inp, E, out, read, 0, 0, out_s, 0, 0, 0, 0, E, 0])
    duration = sum(sum(node[7:10]) for node in nodes)
    region = dict(type='region', id=1, begin=0, end_exclusive=3, elements=length,
                  start_subcycles=5000, end_subcycles=5000 + duration)
    return region, nodes, trace


def budget_checks():
    """Actual source packets can exceed the hypothetical FIFO budget.

    Such packets retain every measured input/output/E phase in a whole-region
    serial fallback. Four small operands remain legal when their bytes fit.
    """
    specs = [
        ('four_full_inputs', [(64, 32)] * 4, 32, False, 1024),
        ('four_small_inputs', [(64, 32)] + [(1, 32)] * 3, 32, True, 268),
        ('wide_output', [(64, 32)] + [(1, 32)] * 3, 64, False, 268),
        ('exact_768', [(64, 32)] * 3, 32, True, 768),
        ('byte_769', [(64, 32)] * 3 + [(1, 8)], 32, False, 769),
    ]
    count = 0
    negatives = []
    for label, inputs, output_bits, eligible, input_bytes in specs:
        tensors = tuple([Tensor(n, bits, True) for n, bits in inputs] +
                        [Tensor(64, output_bits, False)])
        out = len(inputs)
        trace = Trace(tensors, (Op(out, 'Add', 64, 1, 64, 1, 1, 0, 1,
                                  tuple(range(out))),), 1, 'synthetic-budget')
        contract = region_replay_contract(trace, 0, 1)
        require(contract['replay_eligible'] == eligible and
                contract['max_input_bytes'] == input_bytes, 'independent payload boundary')
        input_S = sum((n * (bits // 8) + 63) // 64 for n, bits in inputs) * 1000
        output_S = ((64 * (output_bits // 8) + 63) // 64) * 1000
        node = [1, 1, 0, 0, 64, -1, -1, input_S + 17000, 21000,
                output_S + 11000, input_S, 0, 0, output_S, 0, 0, 0, 0, 21000, 0]
        duration = sum(node[7:10])
        region = dict(type='region', id=1, begin=0, end_exclusive=1, elements=64,
                      start_subcycles=5000, end_subcycles=5000 + duration, **contract)
        saved_region, saved_node = deepcopy(region), deepcopy(node)
        for depth in (1, 2, 4, 8):
            receipt = replay_region(region, [node], trace, depth)
            require(receipt['replay_subcycles'] == receipt['source_subcycles'] == duration,
                    'single-packet source time changed')
            require(receipt['E_service_subcycles'] == 21000 and
                    receipt['controller_service_subcycles'] == node[7] + node[9],
                    'unsupported actual input/output work disappeared')
            require(receipt['serial_fallback'] == (not eligible), 'wrong fallback route')
            require(receipt['peak_live_slots'] == (1 if eligible else 0),
                    'oversized source packet was placed in FIFO')
            require(receipt['peak_packet_input_bytes'] == (input_bytes if eligible else 0),
                    'FIFO observed payload hid an overrun')
            require(receipt['source_contract']['max_input_bytes'] == input_bytes,
                    'oversized source payload was hidden')
            require(region == saved_region and node == saved_node, 'source phases mutated')
            count += 1
        bad = dict(region, replay_eligible=not eligible)
        negatives.append(rejected('false_eligibility_' + label,
                                  lambda: replay_region(bad, [node], trace, 2)))
        if label == 'four_full_inputs':
            bad_bytes = dict(region, max_input_bytes=768)
            negatives.append(rejected('underreported_actual_input_bytes',
                                      lambda: replay_region(bad_bytes, [node], trace, 2)))
    return count, negatives


def run():
    cases = 0
    gains = []
    for length in (1, 15, 16, 17, 63, 64, 65, 129, 513):
        for fusion in (False, True):
            region, nodes, trace = fixture(length, fusion)
            for depth in (1, 2, 4, 8):
                result = replay_region(region, nodes, trace, depth)
                require(result['peak_live_slots'] <= depth, 'slot peak')
                require(result['peak_forward_bytes'] <= 256, 'forward peak')
                require(result['output_ACKs'] == len(nodes), 'lost final output ACK')
                if depth == 1:
                    require(result['source_subcycles'] == result['replay_subcycles'], 'depth1 replay')
                elif result['source_subcycles'] > result['replay_subcycles']:
                    gains.append((length, fusion, depth))
                cases += 1
    require(bool(gains), 'test never exercised real S/E overlap')
    region, nodes, trace = fixture(129, True)
    def mutate(change):
        r, n = deepcopy(region), deepcopy(nodes)
        change(r, n)
        replay_region(r, n, trace, 2)
    negatives = []
    negatives.append(rejected('free_E_arithmetic', lambda: mutate(
        lambda r, n: n[0].__setitem__(8, n[0][8] - 1000))))
    negatives.append(rejected('unpaid_S_service', lambda: mutate(
        lambda r, n: n[0].__setitem__(7, n[0][10] - 1))))
    negatives.append(rejected('source_wall_mismatch', lambda: mutate(
        lambda r, n: r.__setitem__('end_subcycles', r['end_subcycles'] + 1))))
    negatives.append(rejected('wrong_forward_tensor', lambda: mutate(
        lambda r, n: n[1].__setitem__(5, 0))))
    negatives.append(rejected('wrong_forward_generation', lambda: mutate(
        lambda r, n: n[1].__setitem__(3, 64))))
    negatives.append(rejected('missing_packet', lambda: mutate(lambda r, n: n.pop())))
    negatives.append(rejected('zero_depth', lambda: replay_region(region, nodes, trace, 0)))
    negatives.append(rejected('early_buffer_overwrite', lambda: check_ownership(
        [[(0, 20), (19, 30)]])))
    costs = dict(load=5, E=[7, 9], store=4)
    events = make_schedule(4, 2, costs)
    def duplicate_E():
        bad = deepcopy(events)
        first = next(e for e in bad if e['tile'] == 0 and e['stage'] == 'E0')
        second = next(e for e in bad if e['tile'] == 1 and e['stage'] == 'E0')
        second['start'], second['end'] = first['start'], first['end']
        check_schedule(bad, 4, 2, costs)
    negatives.append(rejected('same_E_two_consumers', duplicate_E))
    budget_cases, budget_negatives = budget_checks()
    negatives.extend(budget_negatives)
    return dict(passed=True, replay_cases=cases + budget_cases,
                original_replay_cases=cases, FIFO_budget_cases=budget_cases,
                exercised_overlap_cases=len(gains),
                depths=[1, 2, 4, 8], negative_controls=negatives,
                scope='synthetic finite one-E/one-controller replay validation only')


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
