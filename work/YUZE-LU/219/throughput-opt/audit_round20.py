"""Recheck row-service evidence and immutable completed tiles, not live logs."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from resident_row_probe import qualification
from resident_survey import reference
from verify_resident_batch import replay


def main():
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--tiles',type=Path,required=True);p.add_argument('--ir',type=Path,required=True);a=p.parse_args()
    def read(f):return json.loads(f.read_text())
    def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
    probe=a.runtime/'row-services-v1';q=qualification(probe,[probe/f'simulate-{i}.log' for i in range(3)])
    if q!=read(probe/'qualification.json'):raise ValueError('row qualification receipt differs')
    negative=read(probe/'run-result.json')
    if negative['negative']['returncode']==0 or b'row result differs' not in (probe/'negative.log').read_bytes():
        raise ValueError('actual wrong-row fault was not detected')
    ir=read(a.ir);rows=[];rng=random.Random(220203)
    for file in sorted((a.tiles/'generated').glob('region-v209-rows-*.json')):
        data=read(file);tile=data['tile'];plans=data['programs']
        for trial in range(4):
            inputs={}
            for o in tile['graph']['objects'].values():
                if o['kind']!='external' or 'literal' in o:continue
                value=(-32768,32767,0)[trial] if trial<3 else rng.randrange(-(1<<20),1<<20)
                if o['bits']==16:value=max(-32768,min(32767,value))
                inputs[(o['tensor'],o['index'])]=value
            for name,program in plans.items():
                actual=replay(tile,program,inputs)['observed_native_outputs']
                for row,g in enumerate(tile['graphs']):
                    native=execute(g,inputs);expected=reference(ir['primitive_program'],g,inputs)
                    for primitive,record in g['primitive_outputs'].items():
                        key=tile['graph']['primitive_outputs'][f'{row}:{primitive}'];word=actual[key]
                        if word!=native[record]:raise ValueError('row finite-S/native result differs')
                        signed=(word&0xffffffff)-(1<<32) if word&(1<<31) else word&0xffffffff
                        if signed!=expected[primitive]:raise ValueError('row original integer reference differs')
        best_greedy=min((n for n in plans if 'greedy' in n),key=lambda n:plans[n]['total_ticks'])
        best_dp=min((n for n in plans if 'dp' in n),key=lambda n:plans[n]['total_ticks'])
        rows.append({'file':file.name,'sha256':sha(file),'rows':tile['rows'],'independent_cases_per_plan':4,
            'plans':{n:{k:v[k] for k in ('width','rank_policy','total_ticks','copy_ticks','native_service_ticks','external_words')} for n,v in plans.items()},
            'strongest_greedy':best_greedy,'strongest_dp':best_dp,
            'dp_vs_strongest_greedy_fraction':1-plans[best_dp]['total_ticks']/plans[best_greedy]['total_ticks']})
    if not rows:raise ValueError('no immutable completed row tiles to audit')
    stress_root=Path('work/YUZE-LU/219/throughput-opt/results/resident-overlap-stress-terminal-r20')
    stress=read(stress_root/'stress-result.json');lines=[json.loads(line) for line in (stress_root/'stress.log').read_text().splitlines()]
    if (not stress['passed'] or stress['repeats']!=12 or len(lines)!=12 or
        any(not row['passed'] or row['schedule_sha256']!=stress['schedule_sha256'] for row in lines) or
        'numpy' in stress['modules']):raise ValueError('independent pure-trace stress incomplete')
    result={'passed':True,'row_service_proof':q['proof'],'row_formats':q['formats'],'wrong_row_fault':negative['negative'],
        'independent_tiles':rows,'independent_stress':{k:stress[k] for k in ('passed','repeats','python','malloc','schedule_sha256','code_sha256')},
        'stress_state':(stress_root/'slurm.psv').read_text(),'ir_sha256':sha(a.ir),'audit_sha256':sha(Path(__file__)),
        'scope':'288 prepared-word native row services per SRAM state, independent source/finite-S cold tile numerics and repeated actor scheduling; no actual-weight batched loop, complete row-program RTL, full-loop mapping, system or energy/token/s qualification'}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('independent_tiles','independent_stress','stress_state')}))


if __name__=='__main__':main()
