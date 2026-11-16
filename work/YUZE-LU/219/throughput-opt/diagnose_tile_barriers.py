"""Explain launch barriers in a checked append-only tile phase plan.

Idle intervals are opportunities for a new protocol, not time savings. Earlier
child launch would still require exact channel, S, context and ACK validation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'project/experiments/block_synthesis'))
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def analyse(ir,plan):
    audit={'native':verify_cost(ir),'schedule':verify(ir['tasks'],ir['hardware'],plan)}
    h=ir['hardware']
    if h.get('window_calendar') or any(v!=1 for v in h['resources'].values()):
        raise ValueError('barrier diagnostic currently requires exclusive append-only resources')
    by_id={t['id']:t for t in ir['tasks']};release={r:0 for r in h['resources']};done={};records=[]
    for row in plan['tasks']:
        t=by_id[row['id']];b=next(b for b in t['bindings'] if b['id']==row['binding'])
        ready=max((done[p] for p in t.get('after',[])),default=0)
        if b.get('phase_execution',{}).get('kind')=='native-tile-compound-fcfs-v1':
            children=[]
            for c,s in zip(b['parallel_shards']['children'],row['evaluation']['services']):
                leaf=c['binding'];private={r:release[r] for r in leaf['resources'] if not r.startswith('virtual-memory.channel.')}
                at=max([ready]+list(private.values()))
                children.append({'columns':c['columns'],'macro_binding':leaf['macro_binding'],
                    'actual_start':s['start'],'private_and_data_ready':at,
                    'earlier_private_launch_opportunity_ticks':s['start']-at,
                    'private_releases':private,'solo_ticks':leaf['ticks'],
                    'channel_arbitration_wait_ticks':s['evaluation']['channel_wait_ticks']})
            records.append({'task':t['id'],'start':row['start'],'end':row['end'],'data_ready':ready,
                'channel_releases':{r:release[r] for r in b['resources'] if r.startswith('virtual-memory.channel.')},
                'children':children})
        if 'phase_execution' in b or 'parallel_shards' not in b:
            for r in b['resources']:release[r]=max(release[r],row['end'])
        else:
            for c,s in zip(b['parallel_shards']['children'],row['evaluation']['services']):
                for r in c['binding']['resources']:release[r]=max(release[r],s['end'])
        done[t['id']]=row['end']
    return {'passed':True,'audits':audit,'makespan':plan['makespan'],'phase_compounds':records,
        'summed_child_private_launch_opportunity_ticks':sum(c['earlier_private_launch_opportunity_ticks']
            for r in records for c in r['children']),
        'scope':'idle private launch intervals under selected common-start protocol; neither executable savings nor hardware utilization'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('plan',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();ir=json.loads(a.ir.read_text());plan=json.loads(a.plan.read_text());r=analyse(ir,plan)
    r['inputs']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.ir,a.plan)}
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'makespan':r['makespan'],'compounds':len(r['phase_compounds']),
                      'summed_child_private_launch_opportunity_ticks':r['summed_child_private_launch_opportunity_ticks']}))
