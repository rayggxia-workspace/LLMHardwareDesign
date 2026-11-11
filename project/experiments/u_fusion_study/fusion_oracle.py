"""Finite-buffer/one-E resource oracle and bounded integer forwarding examples.

This is independent executable software, not the C++ performance model, RTL,
or complete tensor inference. Numerical examples use an explicit two-Product
S32/RNE contract and do not qualify every operation in the real trace.
"""
from copy import deepcopy
from fractions import Fraction
import json
import random


LO, HI = -(1 << 31), (1 << 31) - 1


def need(value, message):
    if not value:
        raise AssertionError(message)


def round_packet(value, shift):
    magnitude = abs(value)
    q, r = divmod(magnitude, 1 << shift)
    half = 1 << shift
    q += int(2 * r > half or (2 * r == half and q % 2))
    return min(HI, max(LO, -q if value < 0 else q))


def reference(a, b, c, shifts):
    # Whole-array passes, exact rational ties-to-even, quantize EVERY operator.
    first = [min(HI, max(LO, round(Fraction(x * y, 1 << shifts[0]))))
             for x, y in zip(a, b)]
    return [min(HI, max(LO, round(Fraction(x * y, 1 << shifts[1]))))
            for x, y in zip(first, c)]


def forwarded(a, b, c, shifts, packet):
    output = []
    for start in range(0, len(a), packet):
        stop = min(len(a), start + packet)
        register = [round_packet(a[i] * b[i], shifts[0]) for i in range(start, stop)]
        output.extend(round_packet(x * c[start + j], shifts[1])
                      for j, x in enumerate(register))
    return output


def reserve(calendar, earliest, duration):
    begin = earliest
    for left, right in calendar:
        if begin + duration <= left:
            break
        if begin < right:
            begin = right
    calendar.append((begin, begin + duration))
    calendar.sort()
    return begin, begin + duration


def make_schedule(tiles, slots, costs, seed=0):
    """Populate real gaps in one S calendar and ONE E calendar.

    Slots remain owned until the output store ACK, not merely until compute
    finishes. This generic example overlaps S and E without duplicating E.
    """
    rng = random.Random(seed)
    calendars = {'S': [], 'E': []}
    released = [0] * slots
    events = []
    for tile in range(tiles):
        slot, generation = tile % slots, tile // slots
        ready = released[slot]
        stages = [('load', 'S', costs['load'])]
        stages += [('E' + str(i), 'E', cost) for i, cost in enumerate(costs['E'])]
        stages += [('store_ACK', 'S', costs['store'])]
        for stage, resource, cost in stages:
            start, end = reserve(calendars[resource], ready + rng.randrange(4), cost)
            events.append(dict(tile=tile, slot=slot, generation=generation,
                               stage=stage, resource=resource, start=start, end=end))
            ready = end
        released[slot] = ready
    return events


def check_schedule(events, tiles, slots, costs):
    need(tiles > 0 and slots > 0, 'invalid finite scheduler dimensions')
    expected = [('load', 'S', costs['load'])]
    expected += [('E' + str(i), 'E', cost) for i, cost in enumerate(costs['E'])]
    expected += [('store_ACK', 'S', costs['store'])]
    need(len(events) == tiles * len(expected), 'missing/extra work or store ACK')
    resources = {'S': [], 'E': []}
    tile_events = {}
    for event in events:
        key = (event['tile'], event['stage'])
        need(key not in tile_events, 'duplicate event')
        tile_events[key] = event
        need(event['resource'] in resources, 'unbudgeted duplicate functional resource')
        resources[event['resource']].append((event['start'], event['end']))
    for resource, ranges in resources.items():
        ranges.sort()
        need(all(begin >= 0 and end > begin for begin, end in ranges), 'invalid service')
        need(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])),
             'overlapping requests on one ' + resource)
    lifetimes = [[] for _ in range(slots)]
    for tile in range(tiles):
        prior_end = 0
        for stage, resource, service in expected:
            event = tile_events[(tile, stage)]
            need(event['slot'] == tile % slots and event['generation'] == tile // slots,
                 'wrong slot identity/generation')
            need(event['resource'] == resource, 'wrong resource assignment')
            need(event['end'] - event['start'] == service, 'arithmetic/S service disappeared')
            need(event['start'] >= prior_end, 'consumer ran before producer/ACK')
            prior_end = event['end']
        lifetimes[tile % slots].append((tile_events[(tile, 'load')]['start'], prior_end))
    check_ownership(lifetimes)
    makespan = max(event['end'] for event in events)
    E_work = tiles * sum(costs['E'])
    S_work = tiles * (costs['load'] + costs['store'])
    need(makespan >= max(E_work, S_work), 'resource lower bound violated')
    return dict(passed=True, makespan=makespan, E_service=E_work,
                S_service=S_work, E_instances=1, buffer_slots=slots,
                final_ACK_count=tiles, control_savings=0)


def check_ownership(lifetimes):
    for intervals in lifetimes:
        intervals = sorted(intervals)
        need(all(begin >= 0 and end > begin for begin, end in intervals), 'slot lifetime')
        need(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])),
             'slot overwritten before final store ACK')


def check_barrier(input_completion, consumer_start):
    need(bool(input_completion) and consumer_start >= max(input_completion),
         'full-input reduction factor used before all inputs retire')


def rejected(name, action):
    try:
        action()
    except (AssertionError, KeyError):
        return name
    raise AssertionError('negative control accepted: ' + name)


def run():
    rng = random.Random(247)
    numeric_cases = comparisons = 0
    extremes = [LO, HI, -65537, -65536, -3, -2, -1, 0, 1, 2, 3, 65535, 65536]
    for length in (1, 15, 16, 17, 63, 64, 65, 127, 128, 129):
        for shifts in ((0, 0), (1, 1), (7, 3), (15, 15), (31, 7)):
            arrays = [[rng.choice(extremes) if rng.randrange(2) else
                       rng.randrange(-100000, 100001) for _ in range(length)] for _ in range(3)]
            expected = reference(*arrays, shifts)
            for packet in (1, 7, 16, 64):
                need(forwarded(*arrays, shifts, packet) == expected, 'forwarded numeric mismatch')
                numeric_cases += 1
                comparisons += length
    costs = dict(load=5, E=[21, 21], store=4)
    schedule_cases = 0
    for tiles in (1, 2, 3, 7, 17):
        for slots in (1, 2, 3):
            for seed in range(8):
                check_schedule(make_schedule(tiles, slots, costs, seed), tiles, slots, costs)
                schedule_cases += 1
    good = make_schedule(7, 2, costs, 9)
    negatives = []
    def changed(mutator):
        bad = deepcopy(good)
        mutator(bad)
        check_schedule(bad, 7, 2, costs)
    negatives.append(rejected('missing_store_ACK', lambda: changed(lambda e: e.pop())))
    negatives.append(rejected('wrong_generation', lambda: changed(
        lambda e: e[0].__setitem__('generation', 1))))
    negatives.append(rejected('free_second_E', lambda: changed(
        lambda e: e[1].__setitem__('resource', 'E2'))))
    negatives.append(rejected('unpaid_E_work', lambda: changed(
        lambda e: e[1].__setitem__('end', e[1]['end'] - 1))))
    def overlap_E(events):
        first = next(e for e in events if e['tile'] == 0 and e['stage'] == 'E0')
        other = next(e for e in events if e['tile'] == 1 and e['stage'] == 'E0')
        other['start'], other['end'] = first['start'], first['end']
    negatives.append(rejected('same_E_overlap', lambda: changed(overlap_E)))
    def overwrite(events):
        other = next(e for e in events if e['tile'] == 2 and e['stage'] == 'load')
        other['slot'] = 1
    negatives.append(rejected('wrong_live_slot', lambda: changed(overwrite)))
    negatives.append(rejected('overwrite_before_store_ACK', lambda: check_ownership(
        [[(0, 31), (30, 55)], [(4, 24)]])))
    negatives.append(rejected('early_reduction_factor', lambda: check_barrier([7, 12, 31], 30)))
    check_barrier([7, 12, 31], 31)
    # Explicitly detect illegal algebraic fusion through an operator RNE boundary.
    negatives.append(rejected('removed_intermediate_rounding', lambda: need(
        reference([1], [1], [2], (1, 0)) == [round_packet(1 * 1 * 2, 1)],
        'operator-boundary quantization changed')))
    negatives.append(rejected('removed_intermediate_saturation', lambda: need(
        reference([HI], [2], [1], (0, 1)) == [round_packet(HI * 2, 1)],
        'operator-boundary saturation changed')))
    return dict(passed=True, numeric_cases=numeric_cases, output_comparisons=comparisons,
                finite_schedule_cases=schedule_cases, negative_controls=negatives,
                scope='independent generic one-E/one-S finite-buffer event and two-Product '
                      'S32 RNE examples; does not execute/qualify C++ model tensors or RTL')


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
