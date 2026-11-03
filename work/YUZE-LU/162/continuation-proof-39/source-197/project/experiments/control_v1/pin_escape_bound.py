"""Necessary first-step matching for original M11 pins/checkerboard vias.

An odd-parity M11 terminal cannot change layers at its own vertex. Its first
wire edge must use a neighboring even M11 vertex not fixed to another net.
Same-net terminals with intersecting candidate sets are merged optimistically;
disjoint components still need distinct first-step vertices. A deficient Hall
matching proves infeasibility. A complete matching never proves routability.
"""
import collections


def maximum_matching(edges):
    """Unit bipartite matching with iterative alternating-path augmentation."""
    left = [None] * len(edges)
    right = {}
    while True:
        distance = {i: 0 for i, v in enumerate(left) if v is None}
        queue = collections.deque(distance)
        reachable_free = False
        while queue:
            u = queue.popleft()
            for v in edges[u]:
                if v not in right:
                    reachable_free = True
                elif right[v] not in distance:
                    distance[right[v]] = distance[u] + 1
                    queue.append(right[v])
        if not reachable_free:
            break
        augmented = 0
        for root in range(len(edges)):
            if left[root] is not None:
                continue
            stack = [(root, iter(edges[root]))]
            parent = {}
            while stack:
                u, choices = stack[-1]
                try:
                    v = next(choices)
                except StopIteration:
                    distance[u] = float('inf')
                    stack.pop()
                    continue
                if v not in right:
                    while True:
                        left[u] = v
                        right[v] = u
                        if u == root:
                            break
                        u, v = parent[u]
                    augmented += 1
                    break
                mate = right[v]
                if distance.get(mate) == distance[u] + 1:
                    parent[mate] = (u, v)
                    stack.append((mate, iter(edges[mate])))
        assert augmented, 'Alternating-path search failed to make progress'
    return left, right


def inspect(terminals, nx, ny):
    fixed = {}
    for name, ends in terminals.items():
        assert len(ends) >= 2
        for x, y in ends:
            assert 4 <= x < nx-4 and 4 <= y < ny-4
            assert (x, y) not in fixed, 'Duplicate fixed M11 landing'
            fixed[x, y] = name
    groups = []
    odd_count = own_neighbor_count = 0
    for name, ends in terminals.items():
        ports = []
        for x, y in ends:
            if (x+y) % 2 == 0:
                continue
            odd_count += 1
            choices = [(xx, yy) for xx, yy in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]
                       if 4 <= xx < nx-4 and 4 <= yy < ny-4]
            if any(fixed.get(v) == name for v in choices):
                own_neighbor_count += 1
                continue
            ports.append(((x, y), {v for v in choices if v not in fixed}))
        # Union only within a net. Sharing the first-step vertex is legal for
        # that net; requiring one candidate for the entire component is a
        # deliberate optimistic relaxation, never an over-count of demand.
        parent = list(range(len(ports)))
        def root(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        seen = {}
        for i, (_, choices) in enumerate(ports):
            for v in choices:
                if v in seen:
                    a, b = root(i), root(seen[v])
                    parent[a] = b
                else:
                    seen[v] = i
        components = {}
        for i, (point, choices) in enumerate(ports):
            row = components.setdefault(root(i), dict(net=name, terminals=[], choices=set()))
            row['terminals'].append(point)
            row['choices'].update(choices)
        groups.extend(components.values())
    edges = [sorted(g['choices']) for g in groups]
    left, right = maximum_matching(edges)
    unmatched = [i for i, v in enumerate(left) if v is None]
    witness = None
    if unmatched:
        ls, rs = set(unmatched), set()
        queue = collections.deque(unmatched)
        while queue:
            u = queue.popleft()
            for v in edges[u]:
                rs.add(v)
                assert v in right, 'Maximum matching left an augmenting path'
                mate = right[v]
                if mate not in ls:
                    ls.add(mate)
                    queue.append(mate)
        assert set().union(*(set(edges[i]) for i in ls)) == rs
        assert len(ls) > len(rs)
        witness = dict(demand_groups=len(ls), available_first_step_vertices=len(rs),
                       groups=[dict(net=groups[i]['net'], terminals=groups[i]['terminals'], choices=edges[i]) for i in sorted(ls)],
                       available_vertices=sorted(rs))
    return dict(execution_passed=True, whole_system_qualified=False,
                necessary_condition_satisfied=not unmatched,
                fixed_terminal_count=len(fixed), odd_terminal_count=odd_count,
                optimistic_own_net_neighbor_exemptions=own_neighbor_count,
                demand_components=len(groups), matched_components=len(right),
                candidate_vertex_count=len(set().union(*map(set, edges))) if edges else 0,
                first_step_degree_histogram=dict(collections.Counter(map(len, edges))),
                hall_witness=witness,
                scope='Failure-only necessary M11 first-step vertex matching under the original 4um grid, four-cell margin and checkerboard vias. '
                      'Same-net candidate-overlap components are deliberately under-counted. No deficiency does not prove full routing, spacing, PG, RC or 300MHz.')
