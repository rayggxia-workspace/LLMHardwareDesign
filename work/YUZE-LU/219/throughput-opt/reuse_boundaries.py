"""Actual-weight boundary evidence for conditional native expression reuse.

Every original native position and every original live-out commit survives.
Only a bit-identical expression may use an actual SRAM/external ACK copy.
No candidate inter-S paths are enabled by this experiment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from native_reuse import rewrite,verify
from resident_records import plan
from resident_replay import replay
from resident_survey import reference
from resident_timing import audit


def main():
    p=argparse.ArgumentParser()
    for n in ('ir','regions','boundary','output'):p.add_argument(n,type=Path)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    def read(f):return json.loads(f.read_text(encoding='utf-8'))
    def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
    frozen=a.output/'source';frozen.mkdir();sources={}
    for f in [Path(__file__),*Path('project/experiments/block_synthesis').glob('*.py')]:
        (frozen/f.name).write_bytes(f.read_bytes());sources[f.as_posix()]=sha(f)
    (a.output/'source-sha256.json').write_text(json.dumps(sources,indent=2)+'\n')
    ir=read(a.ir);graphs=[g for r in read(a.regions) for g in r['graphs']]
    fixtures=read(a.boundary/'generated/actual-boundary-fixtures.json')
    actors=read(a.boundary/'generated/timed-survey.json')['actors']
    timing=read(a.boundary/'generated/qualification.json');programs={};rows=[];cases=0
    for f in fixtures:
        gi=f['region_index'];g=graphs[gi]
        if gi not in programs:
            start=time.monotonic();r=rewrite(g);programs[gi]={'graph':r,'plans':{}}
            for name,width,rank,use_reuse in (('original_future_greedy',1,'future_copies',False),
                    ('original_future_dp',8,'future_copies',False),('reuse_greedy',1,'copy_cost',True),
                    ('reuse_future_greedy',1,'future_copies',True),('reuse_dp',8,'copy_cost',True),
                    ('reuse_future_dp',8,'future_copies',True)):
                body=plan(r if use_reuse else g,actors,ir['native_constants']['0']['address_words'],
                          width=width,rank_policy=rank,service_timing=timing)
                audit(body,timing);programs[gi]['plans'][name]=body
            print(json.dumps({'phase':'planned','region':gi,'seconds':time.monotonic()-start,
                'logical_ops':len(g['operations']),'optional':verify(r,g)['optional_reuse_points'],
                'plans':{n:{k:v for k,v in b.items() if k in ('total_ticks','external_words','reused_operations','recomputed_duplicate_operations')}
                         for n,b in programs[gi]['plans'].items()}}),flush=True)
        values={(n,i):v for n,i,v in f['inputs']};gold=execute(g,values);original=reference(ir['primitive_program'],g,values)
        for primitive,key in g['primitive_outputs'].items():
            raw=gold[key]&0xffffffff;signed=raw-(1<<32) if raw&(1<<31) else raw
            if signed!=original[primitive]:raise ValueError('source/native integer mismatch')
        for name,b in programs[gi]['plans'].items():
            use_reuse=b.get('value_reuse');actual=replay(programs[gi]['graph'] if use_reuse else g,b,values)
            if use_reuse:
                if actual['logical_native_outputs']!={n['id']:gold[n['output']] for n in g['operations']}:
                    raise ValueError('conditional expression reuse differs from original native work')
            elif actual['observed_native_outputs']!={n['output']:gold[n['output']] for n in g['operations']}:
                raise ValueError('baseline native result differs')
            cases+=1
        rows.append({'sample':f['sample'],'region_index':gi,'element':f['element']})
    (a.output/'programs.json').write_text(json.dumps(programs,separators=(',',':'))+'\n')
    result={'passed':True,'actual_fixtures':len(fixtures),'program_replays':cases,'rows':rows,'source_sha256':sources,
        'input_sha256':{str(f):sha(f) for f in (a.ir,a.regions,a.boundary/'generated/actual-boundary-fixtures.json')},
        'scope':'actual-weight boundaries only; fixed finite actors, no candidate paths; preserves every logical operation and original commit; not full graph/RTL/controller/SystemC/time/energy/token/s'}
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'program_replays':cases}))


if __name__=='__main__':main()
