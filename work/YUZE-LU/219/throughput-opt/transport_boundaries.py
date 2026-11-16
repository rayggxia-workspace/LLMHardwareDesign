"""Replay actual-weight boundary fixtures through candidate transport programs.

Inputs are recovered frozen Qwen boundary values, never host-filled SRAM.
This is not full-model execution or qualification of a controller/data path.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from resident_records import plan
from resident_replay import replay
from resident_survey import reference
from resident_timing import audit


def main():
    p=argparse.ArgumentParser()
    for name in ('ir','regions','boundary','output'):p.add_argument(name,type=Path)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    def read(f):return json.loads(f.read_text(encoding='utf-8'))
    def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
    ir=read(a.ir);graphs=[g for r in read(a.regions) for g in r['graphs']]
    fixtures=read(a.boundary/'generated/actual-boundary-fixtures.json')
    survey=read(a.boundary/'generated/timed-survey.json');actors=survey['actors'];names=tuple(actors)
    timing=read(a.boundary/'generated/qualification.json');programs={};rows=[]
    paths=[{'kind':'resident-transport-candidate-v1','id':s+'->'+d,'source':s,'destination':d,
            'word_bits':128,'ticks':7,'nets':[s+'->'+d+'.bundle'],'resources':[s+'.io',d+'.io',s+'.holding'],
            'protocol':'reserved-sink/source-held-through-write-ack','provenance':'candidate boundary sensitivity only, no P/U path qualification'}
           for s,d in (names,names[::-1])]
    cases=0
    for f in fixtures:
        gi=f['region_index'];g=graphs[gi]
        if g['index']!=f['element']:raise ValueError('actual boundary index differs')
        if gi not in programs:
            programs[gi]={}
            for name,width,enabled in (('baseline',8,False),('greedy_transport',1,True),('dp_transport',8,True)):
                body=plan(g,actors,ir['native_constants']['0']['address_words'],width=width,
                          rank_policy='future_copies',service_timing=timing,transports=paths if enabled else (),transport_net_budget=2)
                audit(body,timing);programs[gi][name]=body
        values={(n,i):v for n,i,v in f['inputs']};gold=execute(g,values);original=reference(ir['primitive_program'],g,values)
        for primitive,key in g['primitive_outputs'].items():
            raw=gold[key]&0xffffffff;signed=raw-(1<<32) if raw&(1<<31) else raw
            if signed!=original[primitive]:raise ValueError('actual native source differs from original integer graph')
        for name,body in programs[gi].items():
            actual=replay(g,body,values)
            if actual['observed_native_outputs']!={n['output']:gold[n['output']] for n in g['operations']}:
                raise ValueError('actual boundary transport replay differs')
            cases+=1
        rows.append({'sample':f['sample'],'region_index':gi,'element':f['element'],'strategies':list(programs[gi])})
    (a.output/'programs.json').write_text(json.dumps(programs,separators=(',',':'))+'\n')
    result={'passed':True,'actual_fixtures':len(fixtures),'program_replays':cases,'rows':rows,
            'inputs_sha256':{str(f):sha(f) for f in (a.ir,a.regions,a.boundary/'generated/actual-boundary-fixtures.json')},
            'source_sha256':{str(f):sha(f) for f in [Path(__file__),*map(lambda n:Path('project/experiments/block_synthesis')/n,
               ('resident_records.py','resident_transports.py','resident_bounds.py','resident_replay.py','resident_timing.py','native_pointwise.py','resident_survey.py'))]},
            'scope':'recovered actual-weight boundaries, unchanged original/native arithmetic and finite-S event replay; candidate transports are unqualified, not full-model/control/physical/SystemC/time/energy/token/s'}
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'actual_fixtures':len(fixtures),'program_replays':cases}))


if __name__=='__main__':main()
