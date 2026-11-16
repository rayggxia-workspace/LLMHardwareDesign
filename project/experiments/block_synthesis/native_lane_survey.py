"""Source-bound dynamic high16 cover versus the identical old native work."""
import argparse,hashlib,json,time
from pathlib import Path
from native_lane_cover import candidates,cover
from resident_batch import plan
from resident_batch_graph import digest
from resident_survey import reference
from verify_resident_batch import replay


def run(source,ir,output,*,width=2):
    source=Path(source);output=Path(output);output.mkdir(exist_ok=False)
    data=json.loads(source.read_text());original=data['tile'];tile=cover(original)
    first=next(p for p in data['programs'].values() if p.get('operand_contract'))
    frozen=output/'source';frozen.mkdir()
    for file in Path(__file__).parent.glob('*.py'):(frozen/file.name).write_bytes(file.read_bytes())
    specs=[('lane_scalar_greedy',1,False,'future_copies','contiguous'),
        ('lane_greedy',1,True,'future_copies','contiguous'),('lane_layout_greedy',1,True,'future_layout','contiguous'),
        ('lane_dp',width,True,'future_copies','contiguous'),('lane_layout_dp',width,True,'future_layout','contiguous'),
        ('lane_scatter_greedy',1,True,'future_layout','choice'),('lane_scatter_dp',width,True,'future_layout','choice')]
    programs={};seconds={}
    for name,w,batch,rank,layout in specs:
        began=time.monotonic()
        p=plan(tile,first['actors'],first['zero_address'],first['row_timing'],first['scalar_timing'],width=w,
            allow_batch=batch,rank_policy=rank,final_layout=layout,operand_contract=first['operand_contract'])
        seconds[name]=time.monotonic()-began
        if p['status']!='planned':raise ValueError('lane cover planning failed')
        programs[name]=p
        print(json.dumps({'phase':name,'ticks':p['total_ticks'],'words':p['external_words'],'seconds':seconds[name]}),flush=True)
    audits={}
    for fixture in data['fixtures']:
        values={(t,i):v for t,i,v in fixture['inputs']}
        for family,plans in ((original,data['programs']),(tile,programs)):
            for name,p in plans.items():
                got=replay(family,p,values);observed=got['observed_native_outputs']
                for rr,g in enumerate(original['graphs']):
                    for primitive,v in reference(ir['primitive_program'],g,values).items():
                        word=observed[family['graph']['primitive_outputs'][f'{rr}:{primitive}']]&0xffffffff
                        if (word-(1<<32) if word&(1<<31) else word)!=v:raise ValueError('lane cover changed original integer result')
                audits[name]={k:v for k,v in got.items() if k!='observed_native_outputs'}
    best=lambda p,names:min(names,key=lambda n:(p[n]['total_ticks'],p[n]['external_words']))
    old_greedy=best(data['programs'],[n for n in data['programs'] if 'greedy' in n])
    greedy=best(programs,[n for n in programs if 'greedy' in n]);dp=best(programs,[n for n in programs if 'dp' in n])
    selected=best(programs,programs)
    summary={'passed':True,'source_file_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'original_tile_sha256':digest(original),'folded_tile_sha256':digest(tile),'dynamic_extractions_removed':len(candidates(original)),
        'plans':{n:{k:p[k] for k in ('total_ticks','external_words','copy_ticks','native_service_ticks','expanded')} for n,p in programs.items()},
        'search_seconds':seconds,'prior_strong_greedy':old_greedy,'prior_strong_greedy_ticks':data['programs'][old_greedy]['total_ticks'],
        'strongest_new_greedy':greedy,'best_dp':dp,'selected':selected,
        'new_family_vs_prior_greedy_fraction':1-programs[selected]['total_ticks']/data['programs'][old_greedy]['total_ticks'],
        'dp_vs_new_strong_greedy_fraction':1-programs[dp]['total_ticks']/programs[greedy]['total_ticks'],
        'scope':'exact dynamic graph cover and mixed-K candidate commands; static literal folds excluded; complete RTL/actual weights/system qualification pending'}
    (output/'programs.json').write_text(json.dumps({'tile':tile,'programs':programs,'fixtures':data['fixtures'],'audits':audits},separators=(',',':'))+'\n')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--width',type=int,default=2);a=p.parse_args();run(a.source,json.loads(a.ir.read_text()),a.output,width=a.width)
