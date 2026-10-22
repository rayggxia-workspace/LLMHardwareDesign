"""Sequential shortest connection routing and deterministic multi-order search.

Both are heuristics. A failed attempt is NOT an infeasibility proof.
"""
import heapq
import random
from collections import Counter, defaultdict
from model import digest
from validate import validate


def route_once(base, nets, order):
    graph = defaultdict(list)
    for key, con in base["connectors"].items():
        a, b = (base["taps"][con[x]]["component"] for x in ("a", "b"))
        graph[a].append((b, key, con["a"], con["b"]))
        graph[b].append((a, key, con["b"], con["a"]))
    selected, owner, used = set(), {}, Counter()
    for index in order:
        net = nets[index]
        driver, targets = net["driver"], net["sinks"]
        tree = {driver}
        owner[driver] = driver
        for sink in targets:
            if sink in tree:
                continue
            queue = [(0, c, "") for c in sorted(tree)]
            heapq.heapify(queue)
            distance = {(c, ""): 0 for c in tree}
            previous, finish = {}, None
            while queue:
                cost, c, incoming = heapq.heappop(queue)
                if distance.get((c, incoming)) != cost:
                    continue
                if c == sink:
                    finish = (c, incoming)
                    break
                for other, key, exit_tap, entry_tap in sorted(graph[c]):
                    info = base["components"][other]
                    if owner.get(other) not in (None, driver):
                        continue
                    if info["kind"] == "output" and other != driver:
                        continue
                    if info["kind"] == "input" and other not in targets:
                        continue
                    if key in selected:
                        continue  # the current tree is already a multi-source start
                    if used[exit_tap] + 1 + (incoming == exit_tap) > base["taps"][exit_tap]["capacity"]:
                        continue
                    if used[entry_tap] + 1 > base["taps"][entry_tap]["capacity"]:
                        continue
                    nxt = (other, entry_tap)
                    new = cost + base["connectors"][key]["cost_units"]
                    if new < distance.get(nxt, float("inf")):
                        distance[nxt], previous[nxt] = new, ((c, incoming), key)
                        heapq.heappush(queue, (new, *nxt))
            if finish is None:
                return None
            state = finish
            while state in previous:
                prior, key = previous[state]
                if key not in selected:
                    selected.add(key)
                    con = base["connectors"][key]
                    used.update([con["a"], con["b"]])
                    for tap in (con["a"], con["b"]):
                        comp = base["taps"][tap]["component"]
                        owner[comp] = driver
                        tree.add(comp)
                state = prior
    solution = {"base_sha256": digest(base), "connectors": sorted(selected)}
    return solution if validate(base, nets, solution)["valid"] else None


def route(base, nets, method="sequential", seed=0, trials=12):
    order = list(range(len(nets)))
    if method == "sequential":
        return route_once(base, nets, order)
    if method != "multi_order":
        raise ValueError(method)
    # Scarce pin access / fanout order plus seeded permutations. This is a
    # transparent search baseline, not a claimed novel routing algorithm.
    orders = [order, sorted(order, key=lambda i: -len(nets[i]["sinks"]))]
    rng = random.Random(seed)
    for _ in range(trials):
        order = order.copy()
        rng.shuffle(order)
        orders.append(order)
    best = None
    for order in orders:
        candidate = route_once(base, nets, order)
        if candidate is not None:
            cost = validate(base, nets, candidate)["custom_cost_units"]
            if best is None or cost < validate(base, nets, best)["custom_cost_units"]:
                best = candidate
    return best
