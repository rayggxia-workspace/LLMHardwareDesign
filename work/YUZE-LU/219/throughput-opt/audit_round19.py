"""Recheck saved source/finite-S/schedule/RTL evidence without rerunning search."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from resident_overlap_probe import analyse_overlap
from resident_replay import replay
from resident_survey import reference
from verify_cover_frontier import verify as schedule_check
from verify_primitive_cost import verify as source_check
from verify_resident_bindings import verify as native_check
from verify_resident_overlap import verify as overlap_check


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--dp-directory',default='overlap-cover-dp-v2');p.add_argument('--greedy-directory',default='overlap-cover-greedy-v2');a=p.parse_args()
    def read(f):return json.loads(f.read_text())
    def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
    pools={};loaded={};utilization=[]
    for name,directory in (('dp',a.dp_directory),('greedy',a.greedy_directory)):
        root=a.root/directory;ir=read(root/'ir.json');summary=read(root/'summary.json');plan=read(root/'selected.json')
        if not summary['passed']:raise ValueError('unfinished graph-cover experiment')
        audit=source_check(ir);native=native_check(ir)
        schedule=schedule_check(ir['tasks'],ir['hardware'],ir['resident_actions'],plan,18)
        pools[name]={'source':audit,'native':native,'schedule':schedule,'makespan':plan['makespan'],
            'external_words':plan['external_words'],'summary_sha256':sha(root/'summary.json'),'ir_sha256':sha(root/'ir.json')}
        loaded[name]=ir
        actions={x['id']:x for x in ir['resident_actions']}
        for row in plan['tasks']:
            if row['id'] not in actions:continue
            binding=next(b for b in actions[row['id']]['bindings'] if b['id']==row['binding'])
            if not binding.get('resident_overlap'):continue
            proof=ir['resident_overlap_proofs'][binding['resident_overlap']['proof']]
            recipe=ir['resident_recipes'][proof['base_recipe']]
            programs=recipe.get('continuation_loop',{}).get('programs',[recipe['plan']])
            native_busy={actor:0 for actor in recipe['plan']['actors']};copy_busy=dict(native_busy)
            for body,certificate,count in zip(programs,proof['bodies'],proof['visits']):
                for event,node in zip(body['events'],certificate['dag']['nodes']):
                    target=copy_busy if event['op'] in ('LOAD','LOAD_ZERO','STORE','STORE_COMMIT') else native_busy
                    target[event['actor']]+=count*node['duration']
            utilization.append({'pool':name,'primitives':recipe['primitives'],'actor_map':binding['resident_region']['actor_map'],
                'duration':binding['ticks'],'native_service_ticks':native_busy,'descriptor_service_ticks':copy_busy,
                'native_service_fraction':{actor:t/binding['ticks'] for actor,t in native_busy.items()},
                'descriptor_service_fraction':{actor:t/binding['ticks'] for actor,t in copy_busy.items()},
                'scope':'per-actor compiler service occupancy inside union reservation, not gate-level active duty or DRAM measurement'})
    traces=read(a.root/'overlap-survey-v2/summary.json');trace_count=0
    for case in traces['cases']:
        c=read(a.root/'overlap-survey-v2'/(case+'.json'))
        for schedule in c['schedules'].values():overlap_check(c['graph'],c['base_program'],c['dag'],schedule,c['dag']['channel_by_actor']);trace_count+=1
    rtl=a.root/'overlap-rtl-v2';m=read(rtl/'manifest.json');acceptance=read(rtl/'acceptance.json')
    reports=[analyse_overlap(rtl,rtl/f'simulate-{i}.log') for i in range(3)]
    original=read(a.root.parent/'issue219-runtime-round18/reuse-rtl-v2/manifest.json')
    by_id={c['id']:c for c in original['cases']};actual=edges=0
    for c in m['cases']:
        source=by_id[c['source_case']]
        for field in ('graph','original_graph','plan','values','expected','physical_window_offsets'):
            if c[field]!=source[field]:raise ValueError('concurrent probe changed source input/program')
        inputs={(n,i):v for n,i,v in c['values']};g=c['graph'];base=c['plan']
        result=replay(g,base,inputs);gold=execute(c['original_graph'],inputs)
        if result['observed_native_outputs']!={n['output']:gold[n['output']] for n in g['operations']}:
            raise ValueError('source numeric result differs')
        if c['description']['kind']=='actual-weight-boundary':
            ref=reference(loaded['dp']['primitive_program'],c['original_graph'],inputs)
            for primitive,key in c['original_graph']['primitive_outputs'].items():
                word=gold[key]&0xffffffff;signed=word-(1<<32) if word&(1<<31) else word
                if signed!=ref[primitive]:raise ValueError('original integer program boundary differs')
            actual+=1
        else:edges+=1
        overlap_check(g,base,c['dag'],c['schedule'],c['channel_by_actor'])
    if acceptance['negative']['ack']['returncode']==0 or b'LOAD before STORE committed' not in (rtl/'ack.log').read_bytes():
        raise ValueError('early-ACK fault was not detected')
    baseline=read(a.root.parent/'issue219-runtime-round18/cover-compare-v1/conditional_reuse/summary.json')
    old=baseline['plans'][baseline['selected']];new=pools['dp']
    result={'passed':True,'pools':pools,'trace_schedule_certificates':trace_count,'actual_weight_probe_programs':actual,
        'diagnostic_probe_programs':edges,'cases_per_initialization':[r['cases'] for r in reports],
        'native_overlap_cycles':[r['native_overlap_cycles'] for r in reports],'utilization':utilization,
        'old_makespan':old['makespan'],'new_makespan':new['makespan'],
        'time_gain_fraction':1-new['makespan']/old['makespan'],
        'external_word_gain_fraction':1-new['external_words']/old['external_words'],
        'internal_dp_over_strong_greedy_pool_fraction':1-new['makespan']/pools['greedy']['makespan'],
        'audit_sha256':sha(Path(__file__)),'scope':'source-closed FFN cut and actual native concurrent boundary programs; not whole-model/system/DMA/SystemC/energy/token/s qualification'}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('pools','utilization')}))


if __name__=='__main__':main()
