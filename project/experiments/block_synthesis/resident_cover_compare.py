"""Search an already registered, immutable common cover pool.

Separate registration from policy runs so a failed/terminal policy need not
recompile the pool or repeat successful experiments. No model-specific rules.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from cover_frontier import search
from resident_utilization import report as utilization
from verify_cover_frontier import verify


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--width',type=int,default=8);p.add_argument('--wire-budget',type=int,default=18)
    p.add_argument('--rank',default='hypergraph_completion',choices=('shared_tail','hypergraph_completion','hypergraph_resources'))
    p.add_argument('--backbone',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
    ir=json.loads(a.ir.read_text());old=json.loads(a.backbone.read_text()) if a.backbone else None
    began=time.monotonic()
    plan=search(ir['tasks'],ir['hardware'],ir['resident_actions'],width=a.width,
                wire_budget=a.wire_budget,backbone=old,rank_policy=a.rank)
    seconds=time.monotonic()-began
    audit=verify(ir['tasks'],ir['hardware'],ir['resident_actions'],plan,a.wire_budget)
    for name,value in (('plan',plan),('utilization',utilization(ir,plan))):
        (a.output/(name+'.json')).write_text(json.dumps(value,separators=(',',':'))+'\n')
    result={'passed':True,'seconds':seconds,'audit':audit,
            'ir_sha256':hashlib.sha256(a.ir.read_bytes()).hexdigest(),
            'backbone_sha256':hashlib.sha256(a.backbone.read_bytes()).hexdigest() if a.backbone else None,
            'summary':{k:plan[k] for k in ('makespan','external_words','wire_cost','multi_task_decisions','expanded')},
            'scope':'bounded common-pool model-cost search and independent schedule audit; not full model/RTL/system/energy/token/s qualification'}
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
