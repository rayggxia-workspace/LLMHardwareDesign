"""Post-run cardinality, unchanged-net preservation and moved-pad checks."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("spec","initial","final","prior"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    initial,final,prior=map(read,[a.initial,a.final,a.prior])
    assert all(x["geometry_check"]["passed"] for x in (initial,final,prior))
    assert initial["context"]==final["context"]
    initial_set=set(initial["routes"])
    final_set=set(final["routes"])
    old=set(prior["routes"])
    assert initial_set<=final_set
    assert len(final_set|set(final["failed"]))==1834
    via_by_net={n:{v["pin"]:v["at"] for v in route["via10"]} for n,route in final["routes"].items()}
    changed=read(a.spec/"lower-evidence.json")
    by_block=defaultdict(set)
    per_port=Counter()
    touched=set()
    for r in changed["rebound"]:
        n=r["net"]
        if n not in final_set:
            continue
        block=r["pin"].split("/")[0]
        x,y,x2,y2=r["new_m10"]
        assert via_by_net[n][r["pin"]]==[(x+x2)//2,(y+y2)//2]
        by_block[block].add(n)
        per_port[block]+=1
        touched.add(n)
    assert len(touched)==final["evidence"]["through_escape"]
    moves=Counter(escape_nets=len(touched),unchanged_top_nets=len(initial_set&final_set),
                  net_gain_after_initial=len(final_set-initial_set),old_job_retained=len(old&final_set),
                  new_since_old_job=len(final_set-old),old_job_absent=len(old-final_set))
    print(json.dumps({"moves":dict(moves),"from_new_ports_by_block":{n:len(ids) for n,ids in by_block.items()},
                      "from_new_ports_endpoint_count":dict(per_port),"final_count":len(final_set),
                      "initial_count":len(initial_set),"families":final["evidence"]},sort_keys=True))


if __name__=="__main__":
    main()
