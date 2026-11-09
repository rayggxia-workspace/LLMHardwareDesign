"""Finite128-bit-record backing allocator; no packing or free copies.

The serial planner emits real reusable addresses, inclusive lifetimes and
allocation generations. Views retain their complete backing. Dense immutable
file permutations share that file's physical record order and retain explicit
strides. This is not a parallel-DP allocation or a complete memory controller.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


class Arena:
    def __init__(self, records):
        if type(records) is not int or not 0 < records <= 2**60:
            raise ValueError('positive finite64bit record address space required')
        self.records, self.free, self.live, self.generation = records, [(0, records)], {}, 0
        self.high_water = self.peak_live = 0

    def allocate(self, owner, records):
        if owner in self.live or type(records) is not int or records < 1:
            raise ValueError('invalid or duplicate allocation')
        choices = [(size, base, i) for i, (base, size) in enumerate(self.free) if size >= records]
        if not choices:
            raise MemoryError('finite external memory exhausted: '+owner)
        size, base, index = min(choices)
        self.free.pop(index)
        if size > records:
            self.free.insert(index, (base+records, size-records))
        self.generation += 1
        allocation = {'address_words': base, 'words': records, 'generation': self.generation}
        self.live[owner] = allocation
        self.high_water = max(self.high_water, base+records)
        self.peak_live = max(self.peak_live, sum(a['words'] for a in self.live.values()))
        return dict(allocation)

    def release(self, owner):
        row = self.live.pop(owner)
        holes = sorted(self.free+[(row['address_words'], row['words'])])
        self.free = []
        for base, size in holes:
            if self.free and sum(self.free[-1]) == base:
                old_base, old_size = self.free.pop()
                self.free.append((old_base, old_size+size))
            else:
                self.free.append((base, size))

    def locate(self, owner, generation, index):
        row = self.live.get(owner)
        if not row or row['generation'] != generation or not 0 <= index < row['words']:
            raise ValueError('stale, missing or out-of-bounds memory access')
        return row['address_words']+index


def dense_file_layout(meta):
    """Prove full dense physical coverage, including transposed axes.

    No name-only coalescing: a slice, broadcast, negative stride or ambiguous
    byte extent is rejected. Source identity is still the caller's frozen-file
    manifest responsibility.
    """
    shape, strides = meta['shape'], meta['source_byte_strides']
    if meta['bits'] != 16 or len(shape) != len(strides) or any(s % 2 or s <= 0 for s in strides):
        raise ValueError('unknown immutable file layout')
    extent = 2
    for size, stride in sorted(zip(shape, strides), key=lambda pair: pair[1]):
        if size == 1:
            continue
        if stride != extent:
            raise ValueError('file view is not a complete dense permutation')
        extent *= size
    if extent != 2*math.prod(shape):
        raise ValueError('file extent differs')
    return [s//2 for s in strides]


def plan_serial(program, capacity_records, scratch_records):
    if type(scratch_records) is not int or scratch_records < 1:
        raise ValueError('explicit positive native scratch reservation required')
    nodes = program['instructions']; end = len(nodes)
    aliases, lifetimes, bindings = {}, {}, {}
    payload_inputs = lambda n: n['inputs'][:1] if n['op'] in ('View', 'Mask') else n['inputs']
    required = {n for node in nodes for n in payload_inputs(node)} | set(program['outputs'].values())
    initial = dict(program['initial_formats'])
    initial['input_ids'] = {'shape': program['input_ids_shape'], 'runtime': True, 'bits': 64}
    file_owners = {}
    def owner(name, words, born, pinned):
        if name in lifetimes:
            raise ValueError('duplicate physical owner')
        lifetimes[name] = {'words': words, 'born': born, 'last': end if pinned else born,
                           'pinned': pinned}
        return name
    for name, meta in initial.items():
        if name not in required:
            continue
        words = math.prod(meta['shape'])
        if words < 1:
            raise ValueError('empty initial tensor')
        if meta.get('source_file') and not meta.get('runtime'):
            strides = dense_file_layout(meta)
            key = (meta['source_file'], meta['source_offset_bytes'], words)
            if key not in file_owners:
                file_owners[key] = owner(name, words, -1, True)
            physical = file_owners[key]
            layout = {'record_strides': strides,
                      'meaning': 'original frozen file record order; do not flatten a transposed alias'}
        else:
            physical = owner(name, words, -1, not meta.get('runtime'))
            layout = {'record_order': 'logical row major'}
        aliases[name] = physical
        bindings[name] = {'owner': physical, 'shape': meta['shape'], **layout}
    owner('_native_scratch', scratch_records, -1, True)
    for name, meta in program.get('predicates', {}).items():
        aliases[name] = owner(name, math.prod(meta['shape']), -1, True)
        bindings[name] = {'owner': name, 'shape': meta['shape'], 'record_order': 'logical row major'}
    for i, node in enumerate(nodes):
        name = node['id']
        if name in aliases:
            raise ValueError('SSA identifier redefined')
        for source in payload_inputs(node):
            if source not in aliases:
                raise ValueError('unresolved payload input: '+source)
            lifetimes[aliases[source]]['last'] = max(lifetimes[aliases[source]]['last'], i)
        if node['op'] in ('View', 'Mask'):
            physical = aliases[node['inputs'][0]]
            layout = {'address_transform': node['attributes'], 'input_names': node['inputs'],
                      'meaning': 'retain original address transform and entire backing; base alone is not a flat view'}
        else:
            # Constant services have no runtime writes in the frozen recipe.
            # Reserve/preload their real regions before execution, not for free
            # at a reused address in the middle of the program.
            pinned = node['op'] == 'Constant'
            physical = owner(name, math.prod(node['shape']), -1 if pinned else i, pinned)
            layout = {'record_order': 'logical row major'}
        aliases[name] = physical
        bindings[name] = {'owner': physical, 'shape': node['shape'], **layout}
    for name in program['outputs'].values():
        lifetimes[aliases[name]]['last'] = end
    arena = Arena(capacity_records); allocations, steps = {}, []
    births, deaths = {}, {}
    for name, life in lifetimes.items():
        births.setdefault(life['born'], []).append(name)
        deaths.setdefault(life['last'], []).append(name)
    for i in range(-1, end+1):
        created, freed = [], []
        for name in sorted(births.get(i, [])):
            allocations[name] = {**arena.allocate(name, lifetimes[name]['words']), **lifetimes[name]}
            created.append(name)
        if i >= 0 and i < end:
            for source in payload_inputs(nodes[i]):
                physical = aliases[source]
                arena.locate(physical, allocations[physical]['generation'], 0)
                arena.locate(physical, allocations[physical]['generation'], allocations[physical]['words']-1)
        for name in sorted(deaths.get(i, [])):
            if i != end:
                arena.release(name); freed.append(name)
        if created or freed:
            steps.append({'instruction': i, 'allocate': created, 'release_after_completion': freed})
    return {'scope': __doc__, 'capacity_records': capacity_records, 'record_bytes': 16,
        'scratch_records': scratch_records, 'allocations': allocations, 'bindings': bindings,
        'steps': steps, 'high_water_bytes': arena.high_water*16,
        'peak_live_bytes_including_initial_constants_predicates_scratch': arena.peak_live*16,
        'physical_initial_file_groups': len(file_owners), 'serial_only': True,
        'parallel_DP_liveness_qualified': False, 'device_time_qualified': False,
        'total_energy_qualified': False, 'allocator_implemented': True}


def audit_intervals(plan):
    """Independent pairwise address/time-overlap audit, not allocator bookkeeping."""
    rows = sorted(plan['allocations'].items(), key=lambda pair: pair[1]['address_words'])
    candidates, pairs = [], 0
    for name, row in rows:
        lo, hi = row['address_words'], row['address_words']+row['words']
        if lo < 0 or row['words'] < 1 or hi > plan['capacity_records']:
            raise ValueError('allocation outside finite memory')
        candidates = [(n, r) for n, r in candidates if r['address_words']+r['words'] > lo]
        for other, old in candidates:
            pairs += 1
            if max(old['born'], row['born']) <= min(old['last'], row['last']):
                raise ValueError('simultaneous address overlap: '+other+' '+name)
        candidates.append((name, row))
    return {'passed': True, 'overlapping_address_interval_pairs_audited': pairs,
            'inclusive_lifetimes': True, 'no_compaction_or_unmodeled_copy': True}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('program', type=Path);p.add_argument('output', type=Path)
    p.add_argument('--capacity-bytes', type=int, required=True)
    p.add_argument('--scratch-records', type=int, required=True)
    a = p.parse_args()
    if a.capacity_bytes % 16:
        raise ValueError('capacity must be a whole number of128bit records')
    plan = plan_serial(json.loads(a.program.read_text()), a.capacity_bytes//16, a.scratch_records)
    plan['independent_interval_audit'] = audit_intervals(plan)
    plan['program_sha256'] = hashlib.sha256(a.program.read_bytes()).hexdigest()
    plan['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with a.output.open('x') as stream:
        json.dump(plan, stream, separators=(',', ':'));stream.write('\n')
    print(json.dumps({k: plan[k] for k in ('high_water_bytes',
        'peak_live_bytes_including_initial_constants_predicates_scratch', 'physical_initial_file_groups')}))


if __name__ == '__main__':
    main()
