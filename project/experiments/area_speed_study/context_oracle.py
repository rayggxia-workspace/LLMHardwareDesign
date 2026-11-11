"""Issue247 independent numeric and finite-lifetime software oracle.

This does not execute SystemC/RTL and is not a performance or tensor-quality test.
The candidate is one S32 row, N8 outputs/context, full signed-96-bit partials,
and one final nearest-even shift followed by signed-32 saturation.
"""
import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random


S32_MIN, S32_MAX = -(1 << 31), (1 << 31) - 1
S96_MIN, S96_MAX = -(1 << 95), (1 << 95) - 1


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def checked96(value):
    check(S96_MIN <= value <= S96_MAX, '96-bit accumulator overflow')
    return value


def saturate32(value):
    return min(S32_MAX, max(S32_MIN, value))


def final_rne(value, shift):
    """Candidate signed nearest-even using floor quotient and positive remainder."""
    check(0 <= shift <= 95, 'unsupported output shift')
    quotient, remainder = divmod(value, 1 << shift)
    halfway = 1 << shift
    if 2 * remainder > halfway or (2 * remainder == halfway and quotient & 1):
        quotient += 1
    return saturate32(quotient)


def owned_blocks(n, worker, workers, pairs):
    """Column ownership derived per column, independently of producer loops."""
    stripe = 16 if pairs else 8
    owned = [c for c in range(n) if (c // stripe) % workers == worker]
    blocks = [owned[i:i + 8] for i in range(0, len(owned), 8)]
    for block in blocks:
        check(block == list(range(block[0], min(block[0] + 8, n))), 'ownership gap')
    return blocks


def numeric_candidate(a, b_columns, contexts, workers, pairs, shift, tile_k=256,
                      fault=None):
    """An explicit context file; unlike the reference, partials interleave by K."""
    n, k = len(b_columns), len(a)
    outputs = {}
    terms = 0
    for worker in range(workers):
        blocks = owned_blocks(n, worker, workers, pairs)
        for first in range(0, len(blocks), contexts):
            group = blocks[first:first + contexts]
            registers = [dict(columns=block, next_k=0, partial=[0] * len(block))
                         for block in group]
            for start in range(0, k, tile_k):
                stop = min(k, start + tile_k)
                retained_a = a[start:stop]
                for ci, block in enumerate(group):
                    target = (ci + 1) % len(group) if fault == 'wrong_context' else ci
                    register = registers[target]
                    check(register['columns'] == block, 'context output tag mismatch')
                    check(register['next_k'] == start, 'K was skipped, repeated or reordered')
                    for lane, column in enumerate(block):
                        delta = 0
                        for offset, av in enumerate(retained_a):
                            delta = checked96(delta + av * b_columns[column][start + offset])
                            terms += 1
                        if fault == 'intermediate_round':
                            delta = final_rne(delta, shift)
                        value = checked96(register['partial'][lane] + delta)
                        if fault == 'truncate48':
                            value = ((value + (1 << 47)) % (1 << 48)) - (1 << 47)
                        if fault == 'intermediate_saturate':
                            value = saturate32(value)
                        register['partial'][lane] = value
                    register['next_k'] = stop
            for register in registers:
                check(register['next_k'] == k, 'incomplete full-K output')
                for column, value in zip(register['columns'], register['partial']):
                    check(column not in outputs, 'duplicate output column')
                    outputs[column] = (saturate32(value) if fault == 'intermediate_round'
                                       else final_rne(value, shift))
    check(sorted(outputs) == list(range(n)), 'lost or padded output column')
    return [outputs[c] for c in range(n)], terms


def reference(a, b_columns, shift):
    # Independent reduction order and independent rounding algorithm.
    return [saturate32(round(Fraction(sum(map(lambda ab: ab[0] * ab[1], zip(a, b))),
                                       1 << shift))) for b in b_columns]


class Lifetime:
    """Checker consumes events; it does not predict scheduling or elapsed time."""
    def __init__(self):
        self.a = [None, None]
        self.b = [None, None]
        self.generations = [0, 0]
        self.contexts = {}
        self.active = False
        self.issued = set()
        self.counts = dict(groups=0, A_loads=0, B_loads=0, A_bytes=0,
                           commands=0, output_ACKs=0, peak_A_banks=0, peak_B_slots=0)

    def apply(self, event):
        op = event['op']
        args = {k: v for k, v in event.items() if k != 'op'}
        getattr(self, op)(**args)
        self.counts['peak_A_banks'] = max(self.counts['peak_A_banks'],
                                         sum(x is not None for x in self.a))
        self.counts['peak_B_slots'] = max(self.counts['peak_B_slots'],
                                         sum(x is not None for x in self.b))

    def begin(self, columns, k, tile_k, n):
        check(not self.active and not any(self.a) and not any(self.b), 'premature group reuse')
        check(columns and len(columns) <= 16, 'context count')
        check(len(set(columns)) == len(columns), 'aliased output contexts')
        check(all(0 <= c < n and c % 8 == 0 for c in columns), 'invalid output tag')
        self.k, self.tile_k, self.n = k, tile_k, n
        self.contexts = {i: dict(column=c, next_k=0, final_retired=False)
                         for i, c in enumerate(columns)}
        self.issued = set()
        self.active = True
        self.counts['groups'] += 1

    def alloc_a(self, bank, generation, start):
        check(self.active and bank in (0, 1), 'A allocation scope')
        check(self.a[bank] is None, 'A overwritten while users remain')
        check(generation == self.generations[bank] + 1, 'A generation alias')
        check(0 <= start < self.k and start % self.tile_k == 0, 'A K range')
        self.generations[bank] = generation
        self.a[bank] = dict(generation=generation, start=start, ack=False,
                            remaining=set(self.contexts))
        self.counts['A_loads'] += 1
        self.counts['A_bytes'] += min(self.tile_k, self.k - start) * 4

    def a_ref(self, bank, generation):
        check(bank in (0, 1), 'invalid A bank')
        value = self.a[bank]
        check(value is not None and value['generation'] == generation, 'stale A generation')
        return value

    def ack_a(self, bank, generation):
        value = self.a_ref(bank, generation)
        check(not value['ack'], 'duplicate A ACK')
        value['ack'] = True

    def alloc_b(self, slot, bank, generation, context, start, column, lanes):
        check(slot in (0, 1) and self.b[slot] is None, 'B overwritten before retirement')
        a = self.a_ref(bank, generation)
        check(a['start'] == start and context in a['remaining'], 'wrong A block/context')
        check(context in self.contexts and self.contexts[context]['column'] == column,
              'wrong output context tag')
        check(lanes == min(8, self.n - column), 'tail column mask')
        check((start, context) not in self.issued, 'duplicate tile issue')
        self.issued.add((start, context))
        self.b[slot] = dict(bank=bank, generation=generation, context=context, start=start,
                           column=column, lanes=lanes, ack=False, consumed=False, output_ack=False)
        self.counts['B_loads'] += 1

    def ack_b(self, slot):
        b = self.b[slot]
        check(b is not None and not b['ack'], 'invalid/duplicate B ACK')
        b['ack'] = True

    def consume(self, slot, context):
        b = self.b[slot]
        check(b is not None and b['ack'] and not b['consumed'], 'B readiness/double consumption')
        a = self.a_ref(b['bank'], b['generation'])
        check(a['ack'], 'read before A input ACK')
        check(b['context'] == context, 'consumer context tag mismatch')
        c = self.contexts[context]
        check(c['next_k'] == b['start'], 'context K continuity')
        check(not c['final_retired'], 'write to retired context')
        c['next_k'] += min(self.tile_k, self.k - b['start'])
        b['consumed'] = True
        self.counts['commands'] += 1

    def ack_output(self, slot):
        b = self.b[slot]
        check(b is not None and b['consumed'] and not b['output_ack'], 'output ACK ordering')
        check(b['start'] + self.tile_k >= self.k, 'output before final K')
        b['output_ack'] = True
        self.counts['output_ACKs'] += 1

    def retire_b(self, slot):
        b = self.b[slot]
        check(b is not None and b['consumed'], 'B retired before consume')
        last = b['start'] + self.tile_k >= self.k
        check(not last or b['output_ack'], 'B retired before output ACK')
        a = self.a_ref(b['bank'], b['generation'])
        check(b['context'] in a['remaining'], 'A reference underflow')
        a['remaining'].remove(b['context'])
        if not a['remaining']:
            self.a[b['bank']] = None
        if last:
            self.contexts[b['context']]['final_retired'] = True
        self.b[slot] = None

    def end(self):
        check(self.active and not any(self.a) and not any(self.b), 'group ended before drain')
        check(all(c['next_k'] == self.k and c['final_retired'] for c in self.contexts.values()),
              'incomplete context or output ACK')
        expected = len(self.contexts) * ((self.k + self.tile_k - 1) // self.tile_k)
        check(len(self.issued) == expected, 'incomplete tile coverage')
        self.active = False


def simulate_lifetimes(n, k, contexts, workers, pairs, rng):
    """Random producer/consumer/ACK delays against the independent checker."""
    events, total = [], dict(cycles=0, groups=0, A_loads=0, B_loads=0, A_bytes=0,
                            commands=0, output_ACKs=0, peak_A_banks=0, peak_B_slots=0)
    expected_groups = 0
    for worker in range(workers):
        state = Lifetime()
        # Each worker has its own private A/B banks and generation counters.
        worker_events = []

        def emit(op, **args):
            event = dict(op=op, **args)
            state.apply(event)
            worker_events.append(event)

        blocks = owned_blocks(n, worker, workers, pairs)
        for first in range(0, len(blocks), contexts):
            columns = [b[0] for b in blocks[first:first + contexts]]
            expected_groups += 1
            emit('begin', columns=columns, k=k, tile_k=256, n=n)
            tasks = [(start, ci, col) for start in range(0, k, 256)
                     for ci, col in enumerate(columns)]
            position, cycle = 0, 0
            a_due, b_due, output_due, retire_due = {}, {}, {}, {}
            while position < len(tasks) or any(state.a) or any(state.b):
                cycle += 1
                check(cycle < 100000, 'lifetime simulation stalled')
                # ACK arrivals may occur in a different order from issue.
                for handle, due in list(a_due.items()):
                    if due <= cycle:
                        emit('ack_a', bank=handle[0], generation=handle[1])
                        del a_due[handle]
                for slot, due in list(b_due.items()):
                    if due <= cycle:
                        emit('ack_b', slot=slot)
                        del b_due[slot]
                for slot, due in list(output_due.items()):
                    if due <= cycle:
                        emit('ack_output', slot=slot)
                        del output_due[slot]
                        retire_due[slot] = cycle + rng.randrange(1, 4)
                for slot, due in list(retire_due.items()):
                    if due <= cycle:
                        emit('retire_b', slot=slot)
                        del retire_due[slot]
                if position < len(tasks) and rng.random() < 0.77:
                    start, ci, col = tasks[position]
                    bank = next((i for i, a in enumerate(state.a)
                                 if a is not None and a['start'] == start), None)
                    if bank is None:
                        bank = next((i for i, a in enumerate(state.a) if a is None), None)
                        if bank is not None:
                            generation = state.generations[bank] + 1
                            emit('alloc_a', bank=bank, generation=generation, start=start)
                            a_due[(bank, generation)] = cycle + rng.randrange(1, 10)
                    slot = next((i for i, b in enumerate(state.b) if b is None), None)
                    if bank is not None and slot is not None:
                        emit('alloc_b', slot=slot, bank=bank,
                             generation=state.a[bank]['generation'], context=ci,
                             start=start, column=col, lanes=min(8, n - col))
                        b_due[slot] = cycle + rng.randrange(1, 10)
                        position += 1
                eligible = []
                for slot, b in enumerate(state.b):
                    if b and b['ack'] and not b['consumed']:
                        a = state.a[b['bank']]
                        if a['ack'] and state.contexts[b['context']]['next_k'] == b['start']:
                            eligible.append(slot)
                if eligible and rng.random() < 0.64:
                    slot = rng.choice(eligible)
                    b = state.b[slot]
                    emit('consume', slot=slot, context=b['context'])
                    if b['start'] + 256 >= k:
                        output_due[slot] = cycle + rng.randrange(1, 12)
                    else:
                        retire_due[slot] = cycle + rng.randrange(1, 5)
            check(not a_due and not b_due and not output_due and not retire_due, 'unretired ACK')
            emit('end')
            total['cycles'] += cycle
        events.append(worker_events)
        for key, value in state.counts.items():
            if key.startswith('peak_'):
                total[key] = max(total[key], value)
            else:
                total[key] += value
    check(total['groups'] == expected_groups, 'group accounting')
    check(total['A_loads'] == expected_groups * ((k + 255) // 256), 'A load reuse accounting')
    check(total['A_bytes'] == expected_groups * k * 4, 'A byte accounting')
    check(total['commands'] == ((n + 7) // 8) * ((k + 255) // 256), 'command accounting')
    check(total['B_loads'] == total['commands'], 'B load accounting')
    check(total['output_ACKs'] == (n + 7) // 8, 'output accounting')
    return total, events


def replay(events):
    state = Lifetime()
    for event in events:
        state.apply(event)
    check(not state.active, 'undrained replay')


def expect_rejected(name, callback):
    try:
        callback()
    except AssertionError:
        return name
    raise AssertionError('negative control escaped: ' + name)


def negative_checks(events):
    failures = []
    first = lambda op: next(i for i, e in enumerate(events) if e['op'] == op)

    def mutation(name, transform):
        changed = deepcopy(events)
        transform(changed)
        failures.append(expect_rejected(name, lambda: replay(changed)))

    mutation('A_overwrite_live_users', lambda e: e.insert(first('alloc_a') + 1,
                                                       deepcopy(e[first('alloc_a')])))
    mutation('stale_A_generation', lambda e: e[first('ack_a')].update(generation=0))
    mutation('B_overwrite_before_retirement', lambda e: e.insert(first('alloc_b') + 1,
                                                               deepcopy(e[first('alloc_b')])))
    mutation('missing_A_input_ACK', lambda e: e.pop(first('ack_a')))
    mutation('missing_B_input_ACK', lambda e: e.pop(first('ack_b')))
    mutation('wrong_consumer_context', lambda e: e[first('consume')].update(context=99))
    mutation('invalid_tail_mask', lambda e: e[first('alloc_b')].update(lanes=9))
    mutation('early_B_retirement', lambda e: e.insert(first('alloc_b') + 1,
                                                     dict(op='retire_b', slot=e[first('alloc_b')]['slot'])))
    mutation('duplicate_consumption', lambda e: e.insert(first('consume') + 1,
                                                        deepcopy(e[first('consume')])))
    mutation('missing_output_ACK', lambda e: e.pop(first('ack_output')))
    mutation('premature_group_end', lambda e: e.insert(1, dict(op='end')))
    mutation('early_output_ACK', lambda e: e.insert(first('alloc_b') + 1,
                                                   dict(op='ack_output', slot=e[first('alloc_b')]['slot'])))
    mutation('reuse_context_before_drain', lambda e: e.insert(first('consume') + 1,
                                                            deepcopy(e[first('begin')])))
    failures.append(expect_rejected('out_of_order_K', lambda: replay([
        dict(op='begin', columns=[0], k=512, tile_k=256, n=8),
        dict(op='alloc_a', bank=0, generation=1, start=256),
        dict(op='ack_a', bank=0, generation=1),
        dict(op='alloc_b', slot=0, bank=0, generation=1, context=0,
             start=256, column=0, lanes=8),
        dict(op='ack_b', slot=0), dict(op='consume', slot=0, context=0)])))

    def numeric_failure(a, b, shift, fault, contexts=2):
        got, _ = numeric_candidate(a, b, contexts, 1, False, shift, tile_k=1, fault=fault)
        check(got == reference(a, b, shift), 'deliberate arithmetic mutation detected')

    failures.append(expect_rejected('wrong_partial_context', lambda: numeric_failure(
        [1, 2], [[j + 1, j + 2] for j in range(9)], 0, 'wrong_context')))
    failures.append(expect_rejected('partial_truncated_to_48_bits', lambda: numeric_failure(
        [S32_MIN] * 8, [[-32768] * 8], 32, 'truncate48')))
    failures.append(expect_rejected('intermediate_RNE', lambda: numeric_failure(
        [1, 1], [[1, 1]], 1, 'intermediate_round')))
    failures.append(expect_rejected('intermediate_saturation', lambda: numeric_failure(
        [S32_MAX, S32_MAX, -S32_MAX], [[1, 1, 1]], 0, 'intermediate_saturate')))
    failures.append(expect_rejected('positive_96_bit_overflow', lambda: checked96(S96_MAX + 1)))
    failures.append(expect_rejected('negative_96_bit_overflow', lambda: checked96(S96_MIN - 1)))
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    rng = random.Random(247)
    numeric_cases = products = output_comparisons = rounding_cases = 0
    for shift in (0, 1, 2, 8, 16, 32, 48, 64, 95):
        for value in (S96_MIN, S96_MAX, -7, -5, -3, -1, 0, 1, 3, 5, 7,
                      (S32_MAX << shift), (S32_MIN << shift)):
            if not S96_MIN <= value <= S96_MAX:
                continue
            check(final_rne(value, shift) == saturate32(round(Fraction(value, 1 << shift))),
                  'nearest-even/saturation reference mismatch')
            rounding_cases += 1
    dimensions = [(1, 1), (9, 7), (17, 255), (33, 256),
                  (65, 257), (137, 513), (257, 33), (17, 11008)]
    for bits in (8, 16):
        low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        for n, k in dimensions:
            a = [rng.randrange(S32_MIN, S32_MAX + 1) for _ in range(k)]
            b = [[rng.randrange(low, high + 1) for _ in range(k)] for _ in range(n)]
            a[0] = S32_MIN
            a[-1] = S32_MAX
            for col in range(n):
                b[col][0] = low if col % 2 else high
                b[col][-1] = high if col % 2 else low
            # Shift preserves observable partial differences rather than saturating every output.
            shift = bits + 8
            expected = reference(a, b, shift)
            for contexts in (1, 2, 4, 8, 16):
                for workers in (1, 2, 3):
                    for pairs in (False, True):
                        actual, count = numeric_candidate(a, b, contexts, workers, pairs, shift)
                        check(actual == expected, 'numeric multi-context/reference mismatch')
                        numeric_cases += 1
                        products += count
                        output_comparisons += n
    lifetime_cases = lifetime_events = 0
    peak_a = peak_b = 0
    trace_digest = hashlib.sha256()
    witness = None
    for contexts in (1, 2, 4, 8, 16):
        for workers in (1, 2, 3):
            for pairs in (False, True):
                for n, k in ((1, 1), (33, 257), (137, 769), (521, 513)):
                    stats, streams = simulate_lifetimes(n, k, contexts, workers, pairs, rng)
                    lifetime_cases += 1
                    peak_a = max(peak_a, stats['peak_A_banks'])
                    peak_b = max(peak_b, stats['peak_B_slots'])
                    for stream in streams:
                        replay(stream)
                        lifetime_events += len(stream)
                        trace_digest.update(json.dumps(stream, sort_keys=True).encode())
                    if contexts == 8 and workers == 2 and pairs and n == 137:
                        witness = streams[0]
    check(witness is not None and peak_a == peak_b == 2, 'dual-buffer coverage')
    rejected = negative_checks(witness)
    report = dict(passed=True, seed=247, numeric_matrix_cases=numeric_cases,
                  candidate_multiply_terms=products, output_comparisons=output_comparisons,
                  independent_rounding_cases=rounding_cases, lifetime_matrix_cases=lifetime_cases,
                  lifetime_events=lifetime_events, lifetime_trace_sha256=trace_digest.hexdigest(),
                  peak_A_banks=peak_a, peak_B_slots=peak_b, negative_controls=rejected,
                  candidate_rows=1, contexts=[1, 2, 4, 8, 16], worker_counts=[1, 2, 3],
                  operand_bits=dict(A=32, B=[8, 16], partial=96, output=32),
                  scope='Independent software arithmetic and bounded-lifetime preconditions; '
                        'not execution of the SystemC scheduler, RTL, real tensors or model quality')
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')


if __name__ == '__main__':
    main()
