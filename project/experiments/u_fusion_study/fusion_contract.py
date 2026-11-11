"""Independent trace legality/capacity ledger for Issue 247 U fusion research.

This describes the frozen model's flattened vector access contract. Its non-Dot
``layout`` integer is NOT a tensor stride description or RTL layout proof.
No model/generator is imported and no trace-sized tensors are allocated.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


ELEMENTWISE = frozenset(('Add', 'Sub', 'Product', 'Convert', 'Compare', 'Select',
                        'Maximum', 'Minimum', 'MaskZero', 'MaskFloor', 'Mask'))
REDUCTIONS = frozenset(('NFactor', 'SquareSum', 'Sum', 'Max'))
CANONICAL = frozenset(('SiLU', 'RoPE', 'Reciprocal'))
_REPLAY_CONTRACTS = {}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


@dataclass(frozen=True)
class Tensor:
    elements: int
    bits: int
    initial: bool


@dataclass(frozen=True)
class Op:
    out: int
    kind: str
    elements: int
    rows: int
    cols: int
    k: int
    batches: int
    shift: int
    layout: int
    inputs: tuple[int, ...]


@dataclass(frozen=True)
class Trace:
    tensors: tuple[Tensor, ...]
    ops: tuple[Op, ...]
    tokens: int
    sha256: str


def read_trace(path: Path) -> Trace:
    raw = Path(path).read_bytes()
    lines = raw.decode('utf-8').splitlines()
    nt, no, tokens = map(int, lines[0].split())
    require(len(lines) == nt + no + 1, 'trace line count')
    tensors = []
    for index, line in enumerate(lines[1:nt + 1]):
        tid, elements, bits, initial = map(int, line.split())
        require(tid == index and elements > 0 and bits > 0 and bits % 8 == 0,
                'tensor declaration')
        require(initial in (0, 1), 'tensor initial flag')
        tensors.append(Tensor(elements, bits, bool(initial)))
    ops, outputs = [], set()
    for line in lines[nt + 1:]:
        fields = line.split()
        out, kind = int(fields[0]), fields[1]
        data = list(map(int, fields[2:10]))
        inputs = tuple(map(int, fields[10:]))
        require(len(inputs) == data[-1], 'operator input count')
        require(0 <= out < nt and out not in outputs, 'duplicate/invalid producer')
        require(all(0 <= t < out for t in inputs), 'non-topological tensor')
        require(data[0] == tensors[out].elements, 'output extent disagreement')
        require(all(x > 0 for x in data[:5]), 'operator extent')
        outputs.add(out)
        ops.append(Op(out, kind, *data[:-1], inputs))
    return Trace(tuple(tensors), tuple(ops), tokens, hashlib.sha256(raw).hexdigest())


def use_occurrences(trace: Trace):
    users = defaultdict(list)
    for index, op in enumerate(trace.ops):
        for port, tid in enumerate(op.inputs):
            users[tid].append((index, port))
    return users


def vector_regions(trace: Trace):
    """Frozen baseline groups equal-extent E ops, with Constant nodes allowed."""
    regions, at = [], 0
    while at < len(trace.ops):
        op = trace.ops[at]
        if op.kind not in ELEMENTWISE:
            at += 1
            continue
        stop = at + 1
        while stop < len(trace.ops):
            nxt = trace.ops[stop]
            if nxt.kind != 'Constant' and not (
                    nxt.kind in ELEMENTWISE and nxt.elements == op.elements):
                break
            stop += 1
        regions.append((at, stop))
        at = stop
    return regions


def region_replay_contract(trace: Trace, begin, stop):
    """Budget hypothetical FIFO payloads without altering actual vector work.

    Four small logical inputs can fit the same 768B data budget. No operand is
    deleted or truncated. A whole oversized region remains measured serial
    source time outside the FIFO replay; its actual fusion/ledger stays intact.
    """
    key = trace.sha256, begin, stop
    cacheable = len(trace.sha256) == 64
    if cacheable and key in _REPLAY_CONTRACTS:
        return dict(_REPLAY_CONTRACTS[key])
    count = trace.ops[begin].elements
    max_operands = max_input = max_output = 0
    for offset in range(0, count, 64):
        n = min(64, count - offset)
        for index in range(begin, stop):
            op = trace.ops[index]
            if op.kind == 'Constant':
                continue
            max_operands = max(max_operands, len(op.inputs))
            size = 0
            for tid in op.inputs:
                tensor = trace.tensors[tid]
                width = tensor.bits // 8
                start = 0 if tensor.elements == 1 else offset % tensor.elements
                take = min(n, tensor.elements - start)
                size += take * width
                if take < n and tensor.elements > 1:
                    size += min(n - take, tensor.elements) * width
            max_input = max(max_input, size)
            max_output = max(max_output, n * (trace.tensors[op.out].bits // 8))
    reasons = []
    if max_input > 768:
        reasons.append('input_payload_exceeds_768')
    if max_output > 256:
        reasons.append('output_payload_exceeds_256')
    result = dict(replay_eligible=not reasons, replay_excluded_reasons=reasons,
                  max_input_operands=max_operands, max_input_bytes=max_input,
                  max_output_bytes=max_output)
    if cacheable:
        _REPLAY_CONTRACTS[key] = result
    return dict(result)


def legal_edges(trace: Trace, adjacent=True):
    """Single input occurrence, S32, exact tile extent; retain op boundaries.

    Adjacent mode needs only one 64-element packet register. Nonadjacent mode
    is an exploration inventory and does NOT claim a finite implementation.
    """
    users = use_occurrences(trace)
    edges, rejected = [], Counter()
    for begin, stop in vector_regions(trace):
        for index in range(begin, stop):
            producer = trace.ops[index]
            if producer.kind not in ELEMENTWISE:
                continue
            uses = users[producer.out]
            if len(uses) != 1:
                rejected['not_single_input_occurrence'] += 1
                continue
            consumer_index, input_port = uses[0]
            consumer = trace.ops[consumer_index]
            if not begin <= consumer_index < stop:
                rejected['outside_region:' + consumer.kind] += 1
                continue
            if adjacent and consumer_index != index + 1:
                rejected['not_immediately_adjacent'] += 1
                continue
            tensor = trace.tensors[producer.out]
            if tensor.bits != 32 or tensor.elements != producer.elements:
                rejected['not_S32_full_extent'] += 1
                continue
            require(consumer.kind in ELEMENTWISE and
                    producer.elements == consumer.elements, 'invalid region edge')
            require(consumer.inputs[input_port] == producer.out, 'input identity')
            chunks, tail = divmod(producer.elements, 64)
            reservations_each_direction = chunks + bool(tail)
            cycles_each_direction = 4 * chunks + ((tail * 4 + 63) // 64)
            edges.append(dict(producer_index=index, consumer_index=consumer_index,
                              tensor=producer.out, input_port=input_port,
                              producer_kind=producer.kind, consumer_kind=consumer.kind,
                              elements=producer.elements, producer_shift=producer.shift,
                              consumer_shift=consumer.shift,
                              producer_layout_flag=producer.layout,
                              consumer_layout_flag=consumer.layout,
                              write_and_read_bytes=producer.elements * 8,
                              S_cycles_saved=2 * cycles_each_direction,
                              S_reservations_saved=2 * reservations_each_direction,
                              register_bytes=min(64, producer.elements) * 4))
    return edges, dict(sorted(rejected.items()))


def analyse(path: Path):
    trace = read_trace(path)
    adjacent, rejected = legal_edges(trace, True)
    inventory, _ = legal_edges(trace, False)
    kinds = Counter(op.kind for op in trace.ops)
    regions = vector_regions(trace)
    contracts = [region_replay_contract(trace, begin, stop) for begin, stop in regions]
    serial_packets = sum(((trace.ops[begin].elements + 63) // 64) *
                         sum(trace.ops[i].kind in ELEMENTWISE for i in range(begin, stop))
                         for (begin, stop), contract in zip(regions, contracts)
                         if not contract['replay_eligible'])
    def ledger(edges):
        return dict(edges=len(edges),
                    kind_pairs=dict(sorted(Counter(e['producer_kind'] + '->' +
                                                   e['consumer_kind'] for e in edges).items())),
                    S_write_plus_read_bytes=sum(e['write_and_read_bytes'] for e in edges),
                    S_cycles_saved=sum(e['S_cycles_saved'] for e in edges),
                    S_reservations_saved=sum(e['S_reservations_saved'] for e in edges))
    return dict(trace_sha256=trace.sha256, tokens=trace.tokens,
                tensors=len(trace.tensors), operators=len(trace.ops),
                vector_regions=len(regions),
                multiple_node_regions=sum(stop - begin > 1 for begin, stop in regions),
                adjacent_one_slot=ledger(adjacent),
                unrestricted_region_inventory=ledger(inventory),
                adjacent_rejections=rejected,
                full_input_reduction_barriers={k: kinds[k] for k in sorted(REDUCTIONS)},
                canonical_already_register_retained={k: kinds[k] for k in sorted(CANONICAL)},
                NExp_elements=sum(op.elements for op in trace.ops if op.kind == 'NExp'),
                replay_eligible_regions=sum(contract['replay_eligible'] for contract in contracts),
                replay_serial_regions=sum(not contract['replay_eligible'] for contract in contracts),
                replay_serial_packets=serial_packets,
                max_source_input_operands=max(c['max_input_operands'] for c in contracts),
                max_source_input_bytes=max(c['max_input_bytes'] for c in contracts),
                contract=dict(E_instances=1, tile_elements=64, temporary_bytes=256,
                              FIFO_input_bytes=768, FIFO_output_bytes=256,
                              FIFO_input_operand_descriptors=4,
                              FIFO_descriptor_control_area='unknown, not implemented',
                              per_operator_arithmetic_and_quantization_preserved=True,
                              unmodelled_command_cycles_saved=0,
                              existing_canonical_register_savings_claimed=0,
                              no_new_numeric_RTL_or_layout_qualification=True),
                scope='static flattened-model inventory; not throughput, DDR savings, '
                      'or implementation qualification')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('traces', nargs='+', type=Path)
    args = parser.parse_args()
    print(json.dumps({str(path): analyse(path) for path in args.traces}, indent=2))


if __name__ == '__main__':
    main()
