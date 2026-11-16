"""Opt-in unchanged-RTL active-prefix placement and traffic comparison."""
import argparse,hashlib,json
from pathlib import Path
import random,time

from resident_batch import plan
from resident_batch_graph import digest,verify
from resident_survey import reference
from verify_resident_batch import replay


def run(source,ir,qualification,output,*,width=8,ready=False):
    source=Path(source);output=Path(output);output.mkdir(exist_ok=False)
    data=json.loads(source.read_text());tile=data['tile'];verify(tile);old=data['programs'];first=next(iter(old.values()))
    frozen=output/'source';frozen.mkdir()
    for file in Path(__file__).parent.glob('*.py'):(frozen/file.name).write_bytes(file.read_bytes())
    specs=[('masked_scalar_greedy',1,False,'future_copies','fixed'),('masked_greedy',1,True,'future_copies','fixed'),
        ('masked_layout_greedy',1,True,'future_layout','fixed'),('masked_cost_greedy',1,True,'copy_cost','fixed'),
        ('masked_dp',width,True,'future_copies','fixed'),('masked_layout_dp',width,True,'future_layout','fixed')]
    if ready:specs += [('masked_ready_greedy',1,True,'future_copies','ready'),('masked_ready_dp',width,True,'future_copies','ready')]
    candidates={};seconds={}
    for name,w,batch,rank,schedule in specs:
        began=time.monotonic();p=plan(tile,first['actors'],first['zero_address'],first['row_timing'],first['scalar_timing'],
            width=w,allow_batch=batch,rank_policy=rank,schedule=schedule,operand_contract=qualification)
        seconds[name]=time.monotonic()-began
        if p['status']!='planned':raise ValueError('masked plan failed: '+str(p))
        candidates[name]=p
        print(json.dumps({'phase':name,'total_ticks':p['total_ticks'],'external_words':p['external_words'],
                          'expanded':p['expanded'],'seconds':seconds[name]}),flush=True)
    fixtures=[];audits={};rng=random.Random(220220);combined={**old,**candidates}
    for trial in range(4):
        values={}
        for obj in tile['graph']['objects'].values():
            if obj['kind']!='external' or 'literal' in obj:continue
            v=(-2147483648,2147483647,0)[trial] if trial<3 else rng.randrange(-(1<<31),1<<31)
            if obj['bits']==16:v=max(-32768,min(32767,v))
            values[(obj['tensor'],obj['index'])]=v
        fixtures.append({'inputs':[[name,index,v] for (name,index),v in values.items()]})
        for name,p in combined.items():
            result=replay(tile,p,values);observed=result['observed_native_outputs']
            for rr,g in enumerate(tile['graphs']):
                for primitive,v in reference(ir['primitive_program'],g,values).items():
                    key=tile['graph']['primitive_outputs'][f'{rr}:{primitive}'];word=observed[key]&0xffffffff
                    if (word-(1<<32) if word&(1<<31) else word)!=v:raise ValueError('active-prefix plan differs from original integer graph')
            audits[name]={k:v for k,v in result.items() if k!='observed_native_outputs'}
    best=lambda names:min(names,key=lambda n:(combined[n]['total_ticks'],combined[n]['external_words']))
    old_greedy=best([n for n in old if 'greedy' in n]);greedy=best([n for n in combined if 'greedy' in n]);dp=best([n for n in combined if 'dp' in n]);selected=best(combined)
    summary={'passed':True,'rows':tile['rows'],'tile_sha256':digest(tile),'width':width,
        'source_file_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'qualification_sha256':digest(qualification),
        'plans':{n:{k:p[k] for k in ('total_ticks','copy_ticks','native_service_ticks','external_words','expanded')} for n,p in combined.items()},
        'search_seconds':seconds,'selected':selected,'strongest_all_greedy':greedy,'best_dp':dp,'prior_greedy':old_greedy,
        'portfolio_vs_prior_guarded_greedy_fraction':1-combined[selected]['total_ticks']/combined[old_greedy]['total_ticks'],
        'dp_vs_strongest_all_greedy_fraction':1-combined[dp]['total_ticks']/combined[greedy]['total_ticks'],
        'numeric_cases_per_plan':4,'scope':'cold finite-S tile with qualified unchanged-RTL inactive read mask; not new arithmetic/weight/loop/full-program RTL/system qualification'}
    for name,obj in (('programs',{'tile':tile,'programs':combined,'fixtures':fixtures,'audits':audits}),('summary',summary)):
        (output/(name+'.json')).write_text(json.dumps(obj,separators=(',',':'))+'\n')
    print(json.dumps(summary),flush=True);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('source','ir','qualification','output'):p.add_argument(name,type=Path)
    p.add_argument('--width',type=int,default=8);p.add_argument('--ready',action='store_true');a=p.parse_args()
    run(a.source,json.loads(a.ir.read_text()),json.loads(a.qualification.read_text()),a.output,width=a.width,ready=a.ready)
