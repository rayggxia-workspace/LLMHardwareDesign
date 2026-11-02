"""Multi-terminal negotiated router; acceptance requires disjoint complete trees.

Grid pitch is four microns. Metal 11/12 is represented by layer 0/1;
checkerboard via sites preserve the existing 2.2 micron cut-spacing rule.
This module does not qualify RC, clock distribution, or native mask geometry.
"""
import collections
import heapq
import random


def route(terminals, nx, ny, seed=0, max_rounds=80, progress=None):
    rng = random.Random(seed)
    fixed, access = {}, {}
    for name, ends in terminals.items():
        assert len(ends) >= 2 and len(set(ends)) == len(ends), name
        for x, y in ends:
            assert (x, y, 0) not in fixed, (name, x, y)
            fixed[x, y, 0] = name
    for name, ends in terminals.items():
        access[name] = []
        for x, y in ends:
            sites = [(x, y)] if (x+y) % 2 == 0 else [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
            for xx, yy in sites:
                if not (4 <= xx < nx-4 and 4 <= yy < ny-4):
                    continue
                stub = [(x,y,0)] + ([(xx,yy,0)] if (xx,yy)!=(x,y) else []) + [(xx,yy,1)]
                if any(fixed.get(v, name) != name for v in stub):
                    continue
                for v in stub:
                    fixed[v] = name
                access[name].append(stub)
                break
            else:
                raise AssertionError(('No reserved access', name, x, y))
    usage = collections.defaultdict(set)
    history = collections.Counter()
    trees, branches, trace = {}, {}, []
    order = list(terminals)
    rng.shuffle(order)
    for iteration in range(max_rounds):
        if iteration:
            order.sort(key=lambda n: -sum(max(0,len(usage[v])-1) for v in trees[n]))
        for number, name in enumerate(order):
            for v in trees.get(name, ()):
                usage[v].discard(name)
            stubs = access[name]
            tree, result = set(stubs[0]), [stubs[0]]
            remaining = list(stubs[1:])
            # A branch attaches to any point of the current tree. Routing each
            # sink independently to the driver would overcount and miss shorts.
            while remaining:
                tx = [v[0] for v in tree]; ty = [v[1] for v in tree]
                xlo,xhi,ylo,yhi = min(tx),max(tx),min(ty),max(ty)
                def lower(v):
                    return max(xlo-v[0],0,v[0]-xhi)+max(ylo-v[1],0,v[1]-yhi)
                stub = min(remaining, key=lambda s: lower(s[-1]))
                remaining.remove(stub)
                start = stub[-1]
                distance, parent = {start:0}, {}
                serial = 0
                queue = [(lower(start),0,serial,start)]
                while queue:
                    _, cost, _, v = heapq.heappop(queue)
                    if cost != distance[v]:
                        continue
                    if v in tree:
                        break
                    x,y,l = v
                    choices = [((x-1,y,l),1 if l==0 else 2),((x+1,y,l),1 if l==0 else 2),
                               ((x,y-1,l),1 if l==1 else 2),((x,y+1,l),1 if l==1 else 2)]
                    if (x+y)%2 == 0:
                        choices.append(((x,y,1-l),3))
                    for w, step in choices:
                        xx,yy,ll = w
                        if not (4 <= xx < nx-4 and 4 <= yy < ny-4) or fixed.get(w,name)!=name:
                            continue
                        penalty = (8+iteration*4)*len(usage[w]) + history[w]*4
                        alt = cost+step+penalty
                        if alt < distance.get(w,10**20):
                            distance[w]=alt;parent[w]=v;serial+=1
                            heapq.heappush(queue,(alt+lower(w),alt,serial,w))
                else:
                    raise AssertionError(('Disconnected tree',seed,iteration,name))
                path = [v]
                while path[-1] != start:
                    path.append(parent[path[-1]])
                path.reverse()
                path = stub[:-1]+path
                result.append(path);tree.update(path)
            trees[name], branches[name] = tree, result
            for v in tree:
                usage[v].add(name)
            if progress and number%100==0:
                progress(dict(round=iteration,routed=number+1,total=len(order)))
        conflicts = {v:len(names)-1 for v,names in usage.items() if len(names)>1}
        trace.append(dict(round=iteration,conflict_nodes=len(conflicts),excess_occupancy=sum(conflicts.values())))
        if progress:
            progress(trace[-1])
        if not conflicts:
            for name, tree in trees.items():
                assert all((*v,0) in tree for v in terminals[name])
                assert all(usage[v]=={name} for v in tree)
                for path in branches[name]:
                    assert all(sum(abs(a-b) for a,b in zip(v,w))==1 for v,w in zip(path,path[1:]))
                # An independent flood verifies every sink reaches the driver.
                adjacency = collections.defaultdict(set)
                for path in branches[name]:
                    for v,w in zip(path,path[1:]):
                        adjacency[v].add(w);adjacency[w].add(v)
                seen = {(*terminals[name][0],0)}; todo=list(seen)
                while todo:
                    for w in adjacency[todo.pop()]:
                        if w not in seen:
                            seen.add(w);todo.append(w)
                assert seen==tree,('Disconnected final tree',name)
            return branches,dict(seed=seed,rounds=trace,final_conflicts=0,net_count=len(terminals),
                                 terminal_count=sum(map(len,terminals.values())),independent_tree_flood=True)
        history.update(conflicts)
    raise AssertionError(('Negotiated tree routing failed',seed,trace[-1]))
