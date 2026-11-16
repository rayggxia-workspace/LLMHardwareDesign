"""Schedule saved selected FFN traces; no native work or data movement removed."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from resident_continuation import visits
from resident_overlap import binding_channels,build,search
from verify_resident_overlap import verify


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('plan',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--width',type=int,default=8);a=p.parse_args();a.output.mkdir(exist_ok=False)
    def read(f):return json.loads(f.read_text())
    ir=read(a.ir);selected=read(a.plan);h=ir['hardware'];actions={x['id']:x for x in ir['resident_actions']}
    frozen=a.output/'source';frozen.mkdir();source={}
    for f in [Path(__file__),*Path('project/experiments/block_synthesis').glob('*.py')]:
        data=f.read_bytes();(frozen/f.name).write_bytes(data);source[f.as_posix()]=hashlib.sha256(data).hexdigest()
    (a.output/'source-sha256.json').write_text(json.dumps(source,indent=2)+'\n')
    summaries=[];cases=[]
    for ri,row in enumerate(x for x in selected['tasks'] if x['id'] in actions):
        binding=next(b for b in actions[row['id']]['bindings'] if b['id']==row['binding']);spec=binding['resident_region']
        recipe=ir['resident_recipes'][spec['recipe']];g=recipe['graph'];programs=recipe.get('continuation_loop',{}).get('programs',[recipe['plan']])
        counts=visits(recipe['continuation_loop']) if recipe.get('continuation_loop') else [recipe['loop']['elements']]
        mapping=spec['actor_map'];alternatives=[('selected-binding',mapping)]
        # A second actual declared binding tests contention on the same fixed
        # hardware. It is isolated-region evidence, not a rescheduled full cut.
        kinds={old:meta['kind'] for old,meta in recipe['plan']['actors'].items()}
        original_channels=binding_channels(recipe['plan'],h,mapping)
        same=len(set(original_channels.values()))==1
        for pg in h['tile_service_bindings']['P']:
            for eg in h['tile_service_bindings']['E']:
                proposed={old:pg if kind=='M' else eg for old,kind in kinds.items()}
                channels=binding_channels(recipe['plan'],h,proposed)
                if (len(set(channels.values()))==1)!=same:
                    alternatives.append(('alternate-declared-binding',proposed));break
            if len(alternatives)>1:break
        for alternative,actor_map in alternatives:
            channel_map=binding_channels(recipe['plan'],h,actor_map)
            totals={name:0 for name in ('makespan_greedy','critical_greedy','dp','backbone_dp')}
            serial=0
            for bi,(body,multiplier) in enumerate(zip(programs,counts)):
                dag=build(g,body,channel_map);solutions={};seconds={};audits={}
                for name,width,policy,backbone in (('makespan_greedy',1,'makespan',None),('critical_greedy',1,'critical_path',None),
                    ('dp',a.width,'critical_path',None),('backbone_dp',a.width,'critical_path','strong')):
                    start=time.monotonic()
                    seed=min((solutions[n] for n in ('makespan_greedy','critical_greedy')),key=lambda s:s['makespan']) if backbone else None
                    solutions[name]=search(dag,width=width,policy=policy,backbone=seed)
                    seconds[name]=time.monotonic()-start;audits[name]=verify(g,body,dag,solutions[name],channel_map)
                    totals[name]+=multiplier*solutions[name]['makespan']
                serial+=multiplier*body['total_ticks']
                case={'region':ri,'primitives':recipe['primitives'],'alternative':alternative,'actor_map':actor_map,
                    'program_index':bi,'visits':multiplier,'graph':g,'base_program':body,'dag':dag,
                    'schedules':solutions,'audits':audits,'seconds':seconds}
                key=f'region-{ri}-{alternative}-program-{bi}'
                (a.output/(key+'.json')).write_text(json.dumps(case,separators=(',',':'))+'\n');cases.append(key)
                print(json.dumps({'phase':key,'events':len(body['events']),'serialized_ticks':body['total_ticks'],
                    'visits':multiplier,'times':{n:s['makespan'] for n,s in solutions.items()},'seconds':seconds}),flush=True)
            strongest=min(('makespan_greedy','critical_greedy'),key=totals.get);winner=min(totals,key=totals.get)
            summaries.append({'region':ri,'primitives':recipe['primitives'],'alternative':alternative,'actor_map':actor_map,
                'channel_map':channel_map,'serialized_ticks':serial,'totals':totals,'strongest_greedy':strongest,'winner':winner,
                'schedule_vs_serial_fraction':1-totals[winner]/serial,'same_trace_search_vs_strong_fraction':1-totals[winner]/totals[strongest]})
    summary={'passed':True,'rows':summaries,'cases':cases,'input_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.ir,a.plan)},
        'scope':'fixed per-actor commands/finite addresses/ACK and identical external traffic; declared channel compiler model; no actual concurrent RTL/controller/DMA/SystemC/physical/time/energy/token-s qualification'}
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
