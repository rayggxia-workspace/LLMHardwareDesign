"""Actual whole-macro metal/cut/pin connectivity, bounded streaming per net.

Same-layer positive area or positive edge contact conducts; a point does not.
Adjacent metal layers connect only through actual CUT geometry. All shapes of
one LEF MTerm/BTerm are one electrode; distinct terminals are never prejoined.
Every conductor component must connect, including stubs without terminals.
"""
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import gzip
import heapq
import json
from pathlib import Path
import re


def contact(a, b):
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return dx >= 0 and dy >= 0 and (dx > 0 or dy > 0)


def compatible(a, b):
    if a == b:
        return True
    if a.startswith('via') and b.startswith('metal'):
        return int(b[5:]) in (int(a[3:]), int(a[3:]) + 1)
    if b.startswith('via') and a.startswith('metal'):
        return compatible(b, a)
    return False


def components(shapes, terminals, brute=False):
    parent = list(range(len(shapes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[b] = a

    electrodes = {}
    counts = Counter()
    for i, (layer, kind, *box) in enumerate(shapes):
        assert re.fullmatch(r'metal(?:[1-9]|10)|via[1-9]', layer), layer
        assert box[0] < box[2] and box[1] < box[3]
        if kind[0] in 'IP':
            term = kind.removesuffix('-via')
            assert term in terminals
            counts[term] += 1
            if term in electrodes:
                join(i, electrodes[term])
            else:
                electrodes[term] = i
    missing = sorted(set(terminals) - set(counts))
    if brute:
        for i, a in enumerate(shapes):
            for j in range(i):
                b = shapes[j]
                if compatible(a[0], b[0]) and contact(a[2:], b[2:]):
                    join(i, j)
    else:
        # X sweep plus Y buckets: exact bbox contact after candidate lookup.
        # Expired shapes are removed; long clock nets need no quadratic scan.
        buckets = defaultdict(set)
        expiry = []
        size = 2000
        layers = {s[0] for s in shapes}
        peers = {a: [b for b in layers if compatible(a, b)] for a in layers}
        for i in sorted(range(len(shapes)), key=lambda k: shapes[k][2]):
            layer, _, x0, y0, x1, y1 = shapes[i]
            while expiry and expiry[0][0] < x0:
                _, old = heapq.heappop(expiry)
                a = shapes[old]
                for y in range(a[3] // size, a[5] // size + 1):
                    bucket = buckets[(a[0], y)]
                    bucket.remove(old)
                    if not bucket:
                        del buckets[(a[0], y)]
            candidates = set()
            for other in peers[layer]:
                for y in range(y0 // size, y1 // size + 1):
                    candidates.update(buckets.get((other, y), ()))
            for j in candidates:
                if contact(shapes[i][2:], shapes[j][2:]):
                    join(i, j)
            for y in range(y0 // size, y1 // size + 1):
                buckets[(layer, y)].add(i)
            heapq.heappush(expiry, (x1, i))
    groups = defaultdict(list)
    for i in range(len(shapes)):
        groups[find(i)].append(i)
    result = sorted(sorted(v) for v in groups.values())
    # An empty, unconnected logical net is explicitly classified, not silently
    # accepted as a connected routed signal. It must have no terminals either.
    passed = not missing and (len(result) == 1 or (not shapes and not terminals))
    return dict(passed=passed, components=len(result), missing_terminals=missing,
                groups=result, terminals=len(terminals), shapes=len(shapes),
                empty_no_terminals=not shapes and not terminals)


def controls():
    def check(shapes, terms, expected):
        a = components(shapes, terms)
        b = components(shapes, terms, brute=True)
        assert a == b and a['passed'] == expected
    m = lambda a, b, c, d, k='wire', l='metal1': (l, k, a, b, c, d)
    check([m(0, 0, 10, 10), m(10, 2, 20, 8)], [], True)
    check([m(0, 0, 10, 10), m(10, 10, 20, 20)], [], False)
    check([m(0, 0, 10, 10), m(11, 0, 20, 10)], [], False)
    stack = [m(0, 0, 10, 10), m(0, 0, 10, 10, l='metal2')]
    check(stack, [], False)
    check(stack + [m(2, 2, 8, 8, l='via1')], [], True)
    check([m(0, 0, 10, 10, 'Iaa'), m(30, 0, 40, 10, 'Iaa')], ['Iaa'], True)
    check([m(0, 0, 10, 10, 'Iaa'), m(30, 0, 40, 10, 'Ibb')], ['Iaa', 'Ibb'], False)
    check([m(0, 0, 10, 10)], ['Iaa'], False)
    check([m(0, 0, 10, 10), m(20, 0, 30, 10), m(10, 2, 20, 8, 'wire-rect')], [], True)
    import random
    rng = random.Random(121776)
    for _ in range(100):
        rows = []
        for i in range(50):
            x, y = rng.randrange(-20, 20), rng.randrange(-20, 20)
            rows.append(m(x, y, x+rng.randrange(1, 15), y+rng.randrange(1, 15),
                          l=rng.choice(['metal1', 'via1', 'metal2', 'via2', 'metal3'])))
        assert components(rows, []) == components(rows, [], brute=True)
    return dict(passed=True, deterministic_cases=9, random_exact_bruteforce_comparisons=100,
                seed=121776)


def batch_check(batch):
    output = []
    for name, shapes, terms in batch:
        result = components(shapes, terms)
        if result['passed']:
            result.pop('groups')
        else:
            result['component_witnesses'] = [dict(shapes=len(g), sample=[shapes[i] for i in g[:3]])
                                              for g in result.pop('groups')[:30]]
        output.append(dict(net=name, **result))
    return output


def nets(path, patches):
    current = None
    shapes, terms, term_ids = [], [], set()
    seen_patches = set()
    with Path(path).open() as stream:
        for line in stream:
            if line.startswith('# NET '):
                if current is not None:
                    yield current, shapes, terms
                _, _, alias, encoded, sigtype = line.split()
                current = bytes.fromhex(encoded).decode()
                shapes = [('metal'+str(layer), 'wire-rect', *box) for layer, box in patches.get(current, [])]
                if current in patches:
                    seen_patches.add(current)
                terms, term_ids = [], set()
            elif line.startswith('# TERM '):
                assert current is not None
                term = line.split()[2]
                assert term not in term_ids
                term_ids.add(term)
                terms.append(term)
            elif not line.startswith('#'):
                a, layer, kind, *box = line.split()
                assert a == alias and len(box) == 4
                shapes.append((layer, kind, *map(int, box)))
    if current is not None:
        yield current, shapes, terms
    assert seen_patches == set(patches), 'DEF RECT net missing from signal geometry'


def audit(geometry, source_def, destination, cpus=16):
    from native_escape import records
    from native_rect_completion import rectangles
    patches = defaultdict(list)
    expected_names = set()
    rectangle_count = 0
    for record in records(Path(source_def)):
        name = re.sub(r'\\(.)', r'\1', record.lstrip().split()[1])
        assert name not in expected_names
        expected_names.add(name)
        for name, layer, *box in rectangles(record):
            name = re.sub(r'\\(.)', r'\1', name)
            patches[name].append((int(layer[5:]), box))
            rectangle_count += 1
    exported_names, skipped, metadata = set(), set(), None
    with Path(geometry).open() as stream:
        for line in stream:
            if line.startswith('# NET '):
                name = bytes.fromhex(line.split()[3]).decode()
                assert name not in exported_names
                exported_names.add(name)
            elif line.startswith('# SKIP '):
                _, _, name, typ = line.split()
                assert typ in ('POWER', 'GROUND')
                skipped.add(bytes.fromhex(name).decode())
            elif line.startswith('# TOTAL '):
                assert metadata is None
                metadata = tuple(map(int, line.split()[2:]))
    assert exported_names.isdisjoint(skipped)
    assert exported_names | (skipped & expected_names) == expected_names, 'Incomplete DEF net coverage'
    assert metadata and metadata[0] == len(exported_names)
    total = Counter()
    failures = []
    iterator = iter(nets(geometry, patches))
    with ProcessPoolExecutor(max_workers=cpus) as pool, gzip.open(destination, 'wt') as output:
        pending = set()
        done = False
        while pending or not done:
            while len(pending) < cpus * 2 and not done:
                batch = []
                for _ in range(64):
                    try:
                        batch.append(next(iterator))
                    except StopIteration:
                        done = True
                        break
                if batch:
                    pending.add(pool.submit(batch_check, batch))
            if pending:
                finished, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in finished:
                    for row in future.result():
                        output.write(json.dumps(row, separators=(',', ':'))+'\n')
                        total['nets'] += 1
                        for key in ('shapes', 'terminals', 'empty_no_terminals'):
                            total[key] += row[key]
                        total['passed' if row['passed'] else 'failed'] += 1
                        if not row['passed'] and len(failures) < 100:
                            failures.append(row)
    assert (total['nets'], total['terminals']) == metadata
    return dict(passed=total['failed'] == 0 and total['nets'] > 0,
                totals=dict(total), native_def_rectangles=rectangle_count, failures=failures,
                exact_all_normal_def_net_coverage=True, exporter_net_terminal_totals=list(metadata),
                scope='All actual non-PG ODB wire/via/special/pin boxes plus independently parsed complete native DEF RECTs. Same-terminal LEF electrode union; exact positive area/edge geometry, no point contacts or inter-metal shortcut. Every conductor component included.')
