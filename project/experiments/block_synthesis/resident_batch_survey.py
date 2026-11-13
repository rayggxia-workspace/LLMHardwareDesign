"""Audit paid row/layout choices on selected source-closed model regions."""
import argparse
import json
from pathlib import Path
import random
import time

from native_pointwise import bind_external,lower
from resident_batch import plan
from resident_batch_graph import build,digest,units
from resident_bindings import uniform_contract
from resident_survey import build_actors,reference
from verify_resident_batch import replay
from verify_resident_bindings import verify as verify_native
from verify_primitive_cost import verify as verify_source


def run(ir,selected,row_timing,output,*,row_counts=(2,4,8),width=4,first=None):
    output=Path(output);output.mkdir(exist_ok=False)
    frozen=output/'source';frozen.mkdir()
    for file in Path(__file__).parent.glob('*.py'):(frozen/file.name).write_bytes(file.read_bytes())
    def save(name,obj):(output/(name+'.json')).write_text(json.dumps(obj,separators=(',',':'))+'\n')
    source_check=verify_source(ir);native_check=verify_native(ir,numeric=False)
    timing=ir['resident_timing'];actors=build_actors(ir,timing);actions={a['id']:a for a in ir['resident_actions']}
    zero=ir['native_constants']['0']['address_words'];rng=random.Random(220202);results=[]
    for row in selected['tasks']:
        if row['id'] not in actions:continue
        binding=next(b for b in actions[row['id']]['bindings'] if b['id']==row['binding'])
        recipe=ir['resident_recipes'][binding['resident_region']['recipe']];names=recipe['primitives']
        if first is not None and names[0]!=first:continue
        loop=uniform_contract(ir,names)
        for count in row_counts:
            if count>loop['elements']:continue
            graphs=[bind_external(lower(ir['primitive_program'],names,i),ir) for i in range(count)]
            start=(ir['required_external_bytes']+15)//16
            # An explicit finite temporary allocation, reused only after the
            # whole row tile commits. No scratch overlaps another live tile.
            limit=start+sum(o['kind']=='produced' for g in graphs for o in g['objects'].values())
            if 16*limit>1<<ir['hardware']['virtual_memory']['address_bits']:
                raise ValueError('row backing exceeds actual descriptor address width')
            tile=build(graphs,scratch_start=start,external_capacity_words=limit,
                       max_rows=max(int(r) for r in row_timing['profile']['P']))
            candidates={};seconds={};audits={}
            # Strong same-action comparisons keep all scalar and grouped
            # choices. The original continued schedule remains a separate
            # baseline; a cold row-tile result does not replace it by fiat.
            for name,w,batch,rank in (('scalar_greedy',1,False,'future_copies'),
                ('batch_greedy',1,True,'future_copies'),('batch_cost_greedy',1,True,'copy_cost'),
                ('batch_dp',width,True,'future_copies'),('batch_layout_greedy',1,True,'future_layout'),
                ('batch_layout_dp',width,True,'future_layout')):
                began=time.monotonic();candidate=plan(tile,actors,zero,row_timing,timing,width=w,allow_batch=batch,rank_policy=rank)
                seconds[name]=time.monotonic()-began
                if candidate['status']!='planned':raise ValueError('row candidate failed: '+str(candidate))
                candidates[name]=candidate
            fixtures=[]
            for trial in range(3):
                values={}
                for obj in tile['graph']['objects'].values():
                    if obj['kind']!='external' or 'literal' in obj:continue
                    key=(obj['tensor'],obj['index'])
                    if key in values:continue
                    value=(0,-32768,32767)[trial] if trial<2 else rng.randrange(-(1<<20),1<<20)
                    if obj['bits']==16:value=max(-32768,min(32767,value))
                    values[key]=value
                fixtures.append({'trial':trial,'inputs':[[name,i,value] for (name,i),value in values.items()]})
                for name,candidate in candidates.items():
                    checked=replay(tile,candidate,values);audits[name]={k:v for k,v in checked.items() if k!='observed_native_outputs'}
                    observed=checked['observed_native_outputs']
                    for row_index,graph in enumerate(graphs):
                        expected=reference(ir['primitive_program'],graph,values)
                        for primitive,value in expected.items():
                            key=tile['graph']['primitive_outputs'][f'{row_index}:{primitive}'];word=observed[key]&0xffffffff
                            actual=word-(1<<32) if word&(1<<31) else word
                            if actual!=value:raise ValueError('row execution differs from original integer program')
            prefix=f'region-{names[0]}-rows-{count}'
            save(prefix,{'tile':tile,'programs':candidates,'audits':audits,'fixtures':fixtures})
            selected_name=min(candidates,key=lambda n:(candidates[n]['total_ticks'],candidates[n]['external_words']))
            greedy_name=min(('scalar_greedy','batch_greedy','batch_cost_greedy','batch_layout_greedy'),key=lambda n:candidates[n]['total_ticks'])
            dp_name=min(('batch_dp','batch_layout_dp'),key=lambda n:candidates[n]['total_ticks'])
            result={'primitives':names,'rows':count,'source_sha256':tile['source_sha256'],'scratch_words':tile['scratch_words'],
                'program_file':prefix+'.json','units':len(units(tile)),'batchable_units':sum(u['batchable'] for u in units(tile)),
                'plans':{name:{k:p[k] for k in ('total_ticks','copy_ticks','native_service_ticks','external_words','expanded')} for name,p in candidates.items()},
                'search_seconds':seconds,'selected':selected_name,'strongest_batch_greedy':greedy_name,
                'best_portfolio_gain_fraction':1-candidates[selected_name]['total_ticks']/candidates[greedy_name]['total_ticks'],
                'strongest_dp':dp_name,
                'dp_vs_strongest_greedy_fraction':1-candidates[dp_name]['total_ticks']/candidates[greedy_name]['total_ticks'],
                'original_continued_region_ticks':row['end']-row['start'],'loop_elements':loop['elements'],
                'numeric_cases_per_plan':3,'scope':'one finite cold row tile; not a new full-loop or whole-model schedule'}
            results.append(result);print(json.dumps(result),flush=True)
    summary={'passed':True,'source_check':source_check,'original_native_check':native_check,'rows':results,
        'input_sha256':{'ir':digest(ir),'selected':digest(selected),'row_timing':digest(row_timing)},
        'scope':'source-closed cold row tiles with finite S, paid layout/backing, exact integer fixtures; full loops/actual weights/RTL/system remain separate'}
    save('summary',summary);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('ir','selected','row_timing','output'):p.add_argument(name,type=Path)
    p.add_argument('--rows',type=int,nargs='+',default=[2,4,8]);p.add_argument('--width',type=int,default=4)
    p.add_argument('--first');a=p.parse_args()
    run(json.loads(a.ir.read_text()),json.loads(a.selected.read_text()),json.loads(a.row_timing.read_text()),a.output,
        row_counts=tuple(a.rows),width=a.width,first=a.first)
