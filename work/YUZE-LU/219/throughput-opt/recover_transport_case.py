"""Recover one terminal failed policy using its unchanged frozen Python source.

Does not restart a live process or repeat successful policy construction.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time


def main():
    p=argparse.ArgumentParser()
    for name in ('snapshot','ir','case','output'):p.add_argument(name,type=Path)
    a=p.parse_args()
    for name in ('snapshot','ir','case','output'):setattr(a,name,getattr(a,name).resolve())
    a.output.mkdir(exist_ok=False);stage=a.output/'source';modules=stage/'project/experiments/block_synthesis';modules.mkdir(parents=True)
    frozen=json.loads((a.snapshot/'manifest.json').read_text())['files'];verified={}
    for relative,expected in frozen.items():
        source=a.snapshot/Path(relative).name
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise ValueError('frozen recovery source changed '+relative)
        target=(stage/'transport_survey.py') if source.name=='transport_survey.py' else modules/source.name
        shutil.copyfile(source,target);verified[relative]=expected
    os.chdir(stage)
    spec=importlib.util.spec_from_file_location('frozen_survey',stage/'transport_survey.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    ir=json.loads(a.ir.read_text());groups={}
    for r in ir['resident_recipes'].values():
        if r.get('continuation_loop'):groups.setdefault(tuple(r['primitives']),r)
    recipe=sorted(groups.values(),key=lambda r:len(r['graph']['operations']),reverse=True)[0]
    sibling=json.loads(a.case.read_text());paths=sibling['programs'][0]['transports'];actors=recipe['plan']['actors']
    start=time.monotonic()
    seq=m.compile_loop(recipe['graph'],recipe['loop'],actors,recipe['plan']['zero_address'],width=8,
                       rank_policy='future_copies',service_timing=ir['resident_timing'],transports=paths,transport_net_budget=2)
    m.verify(recipe['graph'],recipe['loop'],seq,actors,recipe['plan']['zero_address'],ir['resident_timing'])
    checked=m.check(recipe,seq)
    (a.output/'program.json').write_text(json.dumps(seq,separators=(',',':'))+'\n')
    report={'passed':True,'region':0,'strategy':'future_dp','net_budget':2,'extra_ticks':78,
            'numeric_elements':checked,'seconds':time.monotonic()-start,**seq['totals'],
            'traffic':m.attribution(recipe,seq),'frozen_source_sha256':verified,
            'scope':'only the terminal failed v1 strategy, unchanged frozen search source on Linux; candidate path sensitivity, not qualified product performance'}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='frozen_source_sha256'}))


if __name__=='__main__':main()
