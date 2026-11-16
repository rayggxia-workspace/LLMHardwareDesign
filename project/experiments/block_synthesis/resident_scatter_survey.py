"""Compare native M final address alternatives on identical finite-S work."""
import argparse,json,time
from pathlib import Path
from resident_batch import plan
from resident_survey import reference
from verify_resident_batch import replay


def run(source,ir,output,*,width=2):
    source=Path(source);output=Path(output);output.mkdir(exist_ok=False)
    data=json.loads(source.read_text());tile=data['tile'];old=data['programs'];first=next(p for p in old.values() if p.get('operand_contract'))
    frozen=output/'source';frozen.mkdir()
    for p in Path(__file__).parent.glob('*.py'):(frozen/p.name).write_bytes(p.read_bytes())
    programs=dict(old);seconds={}
    for name,w,rank,layout in [('scatter_greedy',1,'future_copies','choice'),('scatter_layout_greedy',1,'future_layout','choice'),
                         ('scatter_dp',width,'future_copies','choice'),('scatter_layout_dp',width,'future_layout','choice'),
                         ('forced_scatter_greedy',1,'future_layout','scatter'),('forced_scatter_dp',width,'future_layout','scatter')]:
        began=time.monotonic()
        p=plan(tile,first['actors'],first['zero_address'],first['row_timing'],first['scalar_timing'],
            width=w,rank_policy=rank,operand_contract=first['operand_contract'],final_layout=layout)
        seconds[name]=time.monotonic()-began
        if p['status']!='planned':raise ValueError('scatter search failed')
        programs[name]=p
        print(json.dumps({'phase':name,'ticks':p['total_ticks'],'words':p['external_words'],'seconds':seconds[name]}),flush=True)
    audits={}
    for fixture in data['fixtures']:
        values={(t,i):v for t,i,v in fixture['inputs']}
        for name,p in programs.items():
            result=replay(tile,p,values);gold=result['observed_native_outputs']
            for rr,g in enumerate(tile['graphs']):
                for primitive,v in reference(ir['primitive_program'],g,values).items():
                    word=gold[tile['graph']['primitive_outputs'][f'{rr}:{primitive}']]&0xffffffff
                    if (word-(1<<32) if word&(1<<31) else word)!=v:raise ValueError('scatter plan differs from original integer work')
            audits[name]={k:v for k,v in result.items() if k!='observed_native_outputs'}
    best=lambda names:min(names,key=lambda n:(programs[n]['total_ticks'],programs[n]['external_words']))
    greedy=best([n for n in programs if 'greedy' in n]);dp=best([n for n in programs if 'dp' in n]);selected=best(programs)
    summary={'passed':True,'width':width,'plans':{n:{k:p[k] for k in ('total_ticks','external_words','copy_ticks','native_service_ticks','expanded')} for n,p in programs.items()},
        'search_seconds':seconds,'best_greedy':greedy,'best_dp':dp,'selected':selected,
        'dp_vs_strongest_greedy_fraction':1-programs[dp]['total_ticks']/programs[greedy]['total_ticks'],
        'scope':'native accumulator row selection and addressed S final writes; no extra copy/packing hardware; finite-S synthetic cold tile, actual RTL pending'}
    (output/'programs.json').write_text(json.dumps({**data,'programs':programs,'audits':audits},separators=(',',':'))+'\n')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--width',type=int,default=2);a=p.parse_args()
    run(a.source,json.loads(a.ir.read_text()),a.output,width=a.width)
