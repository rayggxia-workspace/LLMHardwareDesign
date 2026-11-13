"""Compare ready-DAG/frontier plans against immutable fixed-order tiles."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

from resident_batch import plan
from resident_batch_graph import digest,verify
from resident_survey import reference
from verify_resident_batch import replay


def run(source,ir,output,*,width=8,grouping_policy='windows'):
    source=Path(source);output=Path(output);output.mkdir(exist_ok=False)
    data=json.loads(source.read_text());tile=data['tile'];verify(tile)
    frozen=output/'source';frozen.mkdir()
    for file in Path(__file__).parent.glob('*.py'):(frozen/file.name).write_bytes(file.read_bytes())
    original=data['programs'];first=next(iter(original.values()))
    candidates={};seconds={}
    for name,w,batch,rank in (('ready_scalar_greedy',1,False,'future_copies'),
        ('ready_greedy',1,True,'future_copies'),('ready_layout_greedy',1,True,'future_layout'),
        ('ready_cost_greedy',1,True,'copy_cost'),('ready_dp',width,True,'future_copies'),
        ('ready_layout_dp',width,True,'future_layout')):
        began=time.monotonic();p=plan(tile,first['actors'],first['zero_address'],first['row_timing'],
            first['scalar_timing'],width=w,allow_batch=batch,rank_policy=rank,schedule='ready',grouping_policy=grouping_policy)
        seconds[name]=time.monotonic()-began
        if p['status']!='planned':raise ValueError('ready DAG has no plan: '+str(p))
        candidates[name]=p
        print(json.dumps({'phase':name,'total_ticks':p['total_ticks'],'external_words':p['external_words'],
                          'expanded':p['expanded'],'search_seconds':seconds[name]}),flush=True)
    rng=random.Random(220211);fixtures=[];audits={}
    for trial in range(4):
        values={}
        for obj in tile['graph']['objects'].values():
            if obj['kind']!='external' or 'literal' in obj:continue
            value=(-32768,32767,0)[trial] if trial<3 else rng.randrange(-(1<<20),1<<20)
            if obj['bits']==16:value=max(-32768,min(32767,value))
            values[(obj['tensor'],obj['index'])]=value
        fixtures.append({'inputs':[[name,index,value] for (name,index),value in values.items()]})
        for name,p in {**original,**candidates}.items():
            result=replay(tile,p,values);observed=result['observed_native_outputs']
            for row,g in enumerate(tile['graphs']):
                expected=reference(ir['primitive_program'],g,values)
                for primitive,value in expected.items():
                    key=tile['graph']['primitive_outputs'][f'{row}:{primitive}'];word=observed[key]&0xffffffff
                    if (word-(1<<32) if word&(1<<31) else word)!=value:
                        raise ValueError('ready program differs from original integer operations')
            audits[name]={k:v for k,v in result.items() if k!='observed_native_outputs'}
    combined={**original,**candidates};old_greedy=[n for n in original if 'greedy' in n]
    all_greedy=old_greedy+[n for n in candidates if 'greedy' in n]
    dp=[n for n in combined if 'dp' in n]
    best=lambda names:min(names,key=lambda n:(combined[n]['total_ticks'],combined[n]['external_words']))
    selected=best(combined);strongest=best(all_greedy);best_dp=best(dp);old=best(old_greedy)
    summary={'passed':True,'rows':tile['rows'],'tile_sha256':digest(tile),
        'source_file_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'ir_sha256':digest(ir),'width':width,'grouping_policy':grouping_policy,
        'plans':{n:{k:p[k] for k in ('total_ticks','copy_ticks','native_service_ticks','external_words','expanded')} for n,p in combined.items()},
        'search_seconds':seconds,'selected':selected,'strongest_all_greedy':strongest,'best_dp':best_dp,
        'portfolio_vs_prior_greedy_fraction':1-combined[selected]['total_ticks']/combined[old]['total_ticks'],
        'dp_vs_strongest_all_greedy_fraction':1-combined[best_dp]['total_ticks']/combined[strongest]['total_ticks'],
        'numeric_cases_per_plan':4,'scope':'cold finite-S source-closed tile; no full loop/weight/RTL/system qualification'}
    for name,obj in (('programs',{'tile':tile,'programs':combined,'fixtures':fixtures,'audits':audits}),('summary',summary)):
        (output/(name+'.json')).write_text(json.dumps(obj,separators=(',',':'))+'\n')
    print(json.dumps(summary),flush=True);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('source','ir','output'):p.add_argument(name,type=Path)
    p.add_argument('--width',type=int,default=8);p.add_argument('--grouping-policy',choices=('windows','all'),default='windows');a=p.parse_args()
    run(a.source,json.loads(a.ir.read_text()),a.output,width=a.width,grouping_policy=a.grouping_policy)
