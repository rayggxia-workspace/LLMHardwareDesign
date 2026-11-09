"""Independent U byte/cache/service ledger, with no timing simulation.

Uses ordered LRU keys rather than the C++ model's timestamp/map scan. This
checks the frozen flattened access contract, including U spills inside Dot
flushes. It does not infer DDR latency or permit cache operations to reorder.
"""
from collections import OrderedDict
import argparse
import hashlib
import json
from pathlib import Path

from fusion_contract import (CANONICAL, ELEMENTWISE, REDUCTIONS, legal_edges,
                             read_trace, require, vector_regions)


def up(n, d):
    return (n + d - 1) // d


class Ledger:
    def __init__(self, trace, edges):
        self.trace = trace
        self.cache = OrderedDict()
        self.backing = set()
        self.matrix_backed = set()
        self.initial = {i for i, tensor in enumerate(trace.tensors) if tensor.initial}
        self.initial.update(op.out for op in trace.ops if op.kind == 'Constant')
        self.last = {}
        for index, op in enumerate(trace.ops):
            for tid in op.inputs:
                self.last[tid] = index
        self.omit_write = {edge['producer_index'] for edge in edges}
        self.omit_read = {(edge['consumer_index'], edge['input_port']) for edge in edges}
        self.stats = dict(U_cache_peak_bytes=0, cache_hits=0, cache_misses=0,
                          dirty_evictions=0, dead_lines_discarded=0,
                          U_S_cycles=0, U_S_reservations=0, vector_work_ticks=0,
                          copy_arithmetic_cycles=0, fused_packets=0,
                          S_write_bytes_removed=0, S_read_bytes_removed=0)
        self.S_read_cycles = self.S_write_cycles = 0
        self.node_digest = hashlib.sha256()
        self.node_count = self.region_count = 0
        self.flows = {name: dict(logical_read=0, logical_write=0, bus_read=0,
                                 bus_write=0, descriptors=0)
                      for name in ('U_read', 'U_write', 'KV_write', 'other')}

    def size(self, tid):
        tensor = self.trace.tensors[tid]
        return tensor.elements * (tensor.bits // 8)

    def service(self, size, write=False):
        if size:
            self.stats['U_S_cycles'] += up(size, 64)
            self.stats['U_S_reservations'] += 1
            if write:
                self.S_write_cycles += up(size, 64)
            else:
                self.S_read_cycles += up(size, 64)

    def dma(self, flow, size, write=False, offset=0):
        if not size:
            return
        beats = up(offset % 64 + size, 64)
        side = 'write' if write else 'read'
        self.flows[flow]['logical_' + side] += size
        self.flows[flow]['bus_' + side] += beats * 64
        self.flows[flow]['descriptors'] += 1
        self.stats['U_S_cycles'] += beats
        self.stats['U_S_reservations'] += beats
        if write:
            self.S_read_cycles += beats
        else:
            self.S_write_cycles += beats

    def remove(self, key, discard=False):
        dirty = self.cache.pop(key)
        if discard:
            self.stats['dead_lines_discarded'] += 1
        elif dirty:
            self.dma('U_write', 64, True)
            self.backing.add(key)
            self.stats['dirty_evictions'] += 1

    def touch(self, tid, offset, size, write):
        if not size:
            return
        require(offset + size <= self.size(tid) + 15, 'access outside frozen extent')
        for line in range(offset // 64, (offset + size - 1) // 64 + 1):
            key = tid, line
            if key in self.cache:
                self.stats['cache_hits'] += 1
                self.cache[key] = self.cache[key] or write
                self.cache.move_to_end(key)
            else:
                while len(self.cache) >= 192:
                    self.remove(next(iter(self.cache)))
                if not write:
                    require(tid in self.initial or tid in self.matrix_backed or
                            key in self.backing, 'read before producer write/ACK')
                    self.dma('U_read', 64)
                    self.stats['cache_misses'] += 1
                self.cache[key] = write
            self.stats['U_cache_peak_bytes'] = max(self.stats['U_cache_peak_bytes'],
                                                  len(self.cache) * 64)

    def read(self, tid, offset, size):
        self.touch(tid, offset, size, False)
        self.service(size)

    def write(self, tid, offset, size):
        self.service(size, True)
        self.touch(tid, offset, size, True)

    def discard(self, tid, offset, size):
        if size:
            for line in range(offset // 64, (offset + size - 1) // 64 + 1):
                key = tid, line
                if key in self.cache:
                    self.remove(key, True)

    def flush(self, tid=None):
        # C++ cache map flush order is key order, independent of its LRU stamps.
        for key in sorted(self.cache):
            if tid is None or key[0] == tid:
                self.remove(key)

    def vector(self, begin, stop):
        count = self.trace.ops[begin].elements
        recorded = self.trace.ops[begin].kind in ELEMENTWISE
        if recorded:
            self.region_count += 1
        def snapshot():
            return (self.S_read_cycles * 1000, self.S_write_cycles * 1000,
                    sum(flow['bus_read'] for flow in self.flows.values()),
                    sum(flow['bus_write'] for flow in self.flows.values()))
        for offset in range(0, count, 64):
            n = min(64, count - offset)
            for index in range(begin, stop):
                op = self.trace.ops[index]
                if op.kind == 'Constant':
                    continue
                before_input = snapshot() if recorded else None
                forward_input = -1
                for port, tid in enumerate(op.inputs):
                    tensor = self.trace.tensors[tid]
                    if (index, port) in self.omit_read:
                        self.stats['S_read_bytes_removed'] += n * 4
                        forward_input = tid
                        continue
                    width, total = tensor.bits // 8, tensor.elements
                    start = 0 if total == 1 else offset % total
                    take = min(n, total - start)
                    self.read(tid, start * width, take * width)
                    if take < n and total > 1:
                        self.read(tid, 0, min(n - take, total) * width)
                after_input = snapshot() if recorded else None
                self.stats['vector_work_ticks'] += up(n, 4) + 5
                width = self.trace.tensors[op.out].bits // 8
                if index in self.omit_write:
                    self.stats['S_write_bytes_removed'] += n * 4
                    self.stats['fused_packets'] += 1
                else:
                    self.write(op.out, offset * width, n * width)
                for tid in op.inputs:
                    tensor = self.trace.tensors[tid]
                    if self.last.get(tid) == index and (tensor.elements == count or offset + n == count):
                        width = tensor.bits // 8
                        self.discard(tid, offset * width if tensor.elements == count else 0,
                                     min(n, tensor.elements) * width)
                if recorded:
                    after_output = snapshot()
                    inp = [b - a for a, b in zip(before_input, after_input)]
                    out = [b - a for a, b in zip(after_input, after_output)]
                    self.node_count += 1
                    facts = [self.node_count, self.region_count, index, offset, n,
                             forward_input, op.out if index in self.omit_write else -1,
                             inp[0], inp[1], out[0], out[1], inp[2], inp[3], out[2], out[3],
                             (up(n, 4) + 5) * 1000]
                    self.node_digest.update((json.dumps(facts, separators=(',', ':')) + '\n').encode())

    def canonical(self, index):
        op = self.trace.ops[index]
        micro = {'SiLU': 41, 'RoPE': 3, 'Reciprocal': 128}[op.kind]
        for offset in range(0, op.elements, 64):
            n = min(64, op.elements - offset)
            tid = op.inputs[0]
            width = self.trace.tensors[tid].bits // 8
            self.read(tid, offset * width, n * width)
            if len(op.inputs) > 1:
                side = op.inputs[1]
                tensor = self.trace.tensors[side]
                self.read(side, 0, min(n, tensor.elements) * (tensor.bits // 8))
            self.stats['vector_work_ticks'] += (up(n, 4) + 5) * micro
            # Existing vecpipe intermediate registers: no extra internal S work.
            self.write(op.out, offset * 4, n * 4)
            if self.last.get(tid) == index:
                self.discard(tid, offset * width, n * width)

    def reduce(self, index):
        op = self.trace.ops[index]
        tid = op.inputs[0]
        tensor = self.trace.tensors[tid]
        width = tensor.bits // 8
        for offset in range(0, tensor.elements, 64):
            n = min(64, tensor.elements - offset)
            self.read(tid, offset * width, n * width)
            self.stats['vector_work_ticks'] += n * 6 if op.kind == 'NFactor' else up(n, 4) * 6
            if self.last.get(tid) == index:
                self.discard(tid, offset * width, n * width)
        self.stats['vector_work_ticks'] += op.elements * (64 if op.kind == 'NFactor' else 3)
        self.write(op.out, 0, self.size(op.out))

    def copy(self, index):
        op = self.trace.ops[index]
        if op.kind == 'Constant':
            return
        if op.kind in ('Gather', 'View'):
            tid = op.inputs[0]
            tensor = self.trace.tensors[tid]
            width = tensor.bits // 8
            for offset in range(0, op.elements, 64):
                n = min(64, op.elements - offset)
                if op.kind == 'Gather':
                    self.dma('other', n * width, offset=offset * width)
                else:
                    start = offset % tensor.elements
                    self.read(tid, start * width, min(n, tensor.elements - start) * width)
                self.stats['copy_arithmetic_cycles'] += up(n, 4) * (6 if op.kind == 'Gather' else 1)
                out_width = self.trace.tensors[op.out].bits // 8
                self.write(op.out, offset * out_width, n * out_width)
            return
        written, wanted = 0, self.size(op.out)
        for tid in op.inputs:
            amount = min(wanted - written, self.size(tid))
            for offset in range(0, amount, 256):
                size = min(256, amount - offset)
                self.read(tid, offset, size)
                self.stats['copy_arithmetic_cycles'] += up(size, 16)
                self.write(op.out, written + offset, size)
                if self.last.get(tid) == index:
                    self.discard(tid, offset, size)
            written += amount
            if written == wanted:
                break
        require(written == wanted, 'copy coverage')

    def run(self):
        regions = dict(vector_regions(self.trace))
        index = 0
        while index < len(self.trace.ops):
            op = self.trace.ops[index]
            if op.kind == 'Dot':
                for tid in op.inputs:
                    self.flush(tid)
                self.matrix_backed.add(op.out)
            elif op.kind == 'KVWrite':
                for tid in op.inputs[:2]:
                    for head in range(2):
                        self.read(tid, head * 512, 512)
                        self.dma('KV_write', 512, True)
            elif op.kind in CANONICAL:
                self.canonical(index)
            elif op.kind in ELEMENTWISE:
                stop = regions[index]
                self.vector(index, stop)
                index = stop
                continue
            elif op.kind in REDUCTIONS:
                self.reduce(index)
            elif op.kind == 'NExp':
                self.vector(index, index + 1)
                self.stats['vector_work_ticks'] += op.elements * 16
            else:
                self.copy(index)
            index += 1
        self.flush()
        return dict(stats=self.stats, flows=self.flows, trace_sha256=self.trace.sha256,
                    event_facts_sha256=self.node_digest.hexdigest(), event_nodes=self.node_count,
                    event_regions=self.region_count,
                    scope='deterministic flattened U access/cache/service counts; no timing simulation')


def derive(path, fused=False):
    trace = read_trace(Path(path))
    edges = legal_edges(trace, adjacent=True)[0] if fused else []
    return Ledger(trace, edges).run()


def check(row, ledger):
    stats = ledger['stats']
    for key in ('U_cache_peak_bytes', 'cache_hits', 'cache_misses', 'dirty_evictions',
                'dead_lines_discarded', 'vector_work_ticks'):
        require(row[key] == stats[key], 'independent U ledger: ' + key)
    h = row['hardware_study']
    require(h['U_service_subcycles'] == stats['U_S_cycles'] * 1000, 'U local S service')
    require(h['U_reservations'] == stats['U_S_reservations'], 'U local S reservation count')
    for name, expected in ledger['flows'].items():
        total = {key: sum(channel['flows'][name][key] for channel in row['detail']['channels'])
                 for key in expected}
        require(total == expected, 'U independent logical/bus/descriptors: ' + name)
    return dict(passed=True, U_cache_flow_and_local_service_independently_replayed=True,
                trace_sha256=ledger['trace_sha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('trace', type=Path)
    parser.add_argument('--fused', action='store_true')
    parser.add_argument('--baseline-json', type=Path)
    args = parser.parse_args()
    result = derive(args.trace, args.fused)
    if args.baseline_json:
        row = json.loads(args.baseline_json.read_text())
        result['check'] = check(row.get('result', row), result)
    print(json.dumps(result, indent=2))
