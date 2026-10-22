"""Exact toy witnesses for a future port/schedule contract; not chip simulation."""
from collections import Counter, deque
from itertools import combinations
from pathlib import Path
import hashlib
import json
import math


def unit_jobs(jobs):
    """Minimum synchronous slots for unit-duration DAG jobs with exclusive units."""
    ids = tuple(jobs)
    index = {name: i for i, name in enumerate(ids)}
    masks = {name: sum(1 << index[p] for p in jobs[name]["after"]) for name in ids}
    full = (1 << len(ids))-1
    queue = deque([(0, [])])
    visited = {0}
    while queue:
        done, witness = queue.popleft()
        if done == full:
            return {"slots":len(witness),"witness":witness,"states":len(visited)}
        ready = [n for n in ids if not done & (1 << index[n]) and done & masks[n] == masks[n]]
        for width in range(1,len(ready)+1):
            for group in combinations(ready,width):
                used = [jobs[n]["unit"] for n in group]
                if len(set(used)) != len(used):
                    continue
                nxt = done | sum(1 << index[n] for n in group)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt,witness+[list(group)]))
    return {"slots":None,"states":len(visited)}


def fifo_pair(order, depth):
    """One emit and/or atomic A+B consume per slot; no same-slot token bypass."""
    pairs = order.count("A")
    assert pairs == order.count("B")
    start = (0,0,0,0)
    queue = deque([(start,[])])
    visited = {start}
    blocked = []
    while queue:
        state, witness = queue.popleft()
        producer, consumer, qa, qb = state
        if producer == len(order) and consumer == pairs:
            return {"slots":len(witness),"witness":witness,"reachable_states":len(visited),"deadlocked":False}
        successors = []
        # Reads see pre-slot tokens. Consumed space may be reused by end-slot writes.
        for consume in (False,True):
            if consume and not (qa > 0 and qb > 0):
                continue
            for produce in (False,True):
                if not (consume or produce) or (produce and producer == len(order)):
                    continue
                a,b = qa-int(consume),qb-int(consume)
                if produce:
                    a += order[producer] == "A"
                    b += order[producer] == "B"
                if a > depth or b > depth:
                    continue
                nxt = (producer+int(produce),consumer+int(consume),a,b)
                successors.append(nxt)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt,witness+[{"emit":order[producer] if produce else None,"consume_pair":consume,"occupancy_after":[a,b]}]))
        if not successors:
            blocked.append(list(state))
    return {"slots":None,"reachable_states":len(visited),"deadlocked":True,"terminal_states":blocked}


def main():
    results = {}
    jobs = {"p0":{"unit":"M","after":[]}, "c0":{"unit":"V","after":["p0"]},
            "p1":{"unit":"M","after":[]}, "c1":{"unit":"V","after":["p1"]}}
    result = unit_jobs(jobs)
    assert result["slots"] == 3
    results["resource_and_path_bounds_not_sufficient"] = {
        "resource_bound":2,"critical_path_bound":2,"exact":result,
        "interpretation":"Two 2-stage jobs require startup/drain even though both scalar lower bounds are 2."}
    renamed = {name:{**job,"unit":"joined_"+job["unit"]} for name,job in jobs.items()}
    assert unit_jobs(renamed)["slots"] == result["slots"]
    results["boundary_label_zero_effect"] = {"split_slots":result["slots"],"joined_slots":unit_jobs(renamed)["slots"],
        "interpretation":"A resource-preserving bijection of ownership/unit labels cannot change feasible schedules."}
    addresses = [0,2]
    lowbit = Counter(address % 2 for address in addresses)
    highbit = Counter((address // 2) % 2 for address in addresses)
    assert max(lowbit.values()) == 2 and max(highbit.values()) == 1
    results["bank_conflict"] = {"word_addresses":addresses,"banks":2,"read_ports_per_bank":1,
        "aggregate_read_bound":math.ceil(len(addresses)/2),"low_address_bit_cycles":max(lowbit.values()),
        "next_address_bit_cycles":max(highbit.values()),
        "interpretation":"Same words and nominal capacity; map choice changes port conflicts. Moving existing data is not free."}
    samebank_reads,samebank_writes = 2,0
    results["port_mode"] = {"reads":samebank_reads,"writes":samebank_writes,
        "one_read_one_write_cycles":max(samebank_reads,samebank_writes),
        "two_read_or_write_cycles":math.ceil((samebank_reads+samebank_writes)/2),
        "interpretation":"Two named ports do not imply equal direction-specific service capacity."}
    for name, order, depth, expected in (
        ("burst_depth_2","AAABBB",2,True),
        ("burst_depth_3","AAABBB",3,False),
        ("alternating_depth_1","ABABAB",1,False)):
        outcome = fifo_pair(order,depth)
        assert outcome["deadlocked"] == expected
        results[name] = {"producer_order":order,"consumer":"atomic A+B","depth_per_edge":depth,**outcome}
    output = {"status":"PASS","scope":"Self-contained exact toy transition systems only; no model weights, hardware timing, physical SRAM, or calibrated accelerator claim.",
        "tests":len(results),"results":results,
        "cycle_convention":"Jobs read pre-slot tokens; completions/writes become visible next slot; no bypass."}
    target = Path(__file__).with_name("minimal-counterexamples-results.json")
    target.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","tests":len(results),"sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "fifo":{k:{"deadlocked":v["deadlocked"],"slots":v["slots"]} for k,v in results.items() if "deadlocked" in v}}))


if __name__ == "__main__":
    main()
