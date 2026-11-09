"""Recheck active-prefix services, complete programs and immutable plan outputs."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from resident_mask_probe import qualification
from resident_batch_probe import analyse
from resident_survey import reference
from verify_resident_batch import replay


def main():
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--server-programs',type=Path,required=True);a=p.parse_args();read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    services=a.runtime/'mask-services-v2';q=qualification(services,[services/f'simulate-{i}.log' for i in range(4)])
    if q!=read(services/'qualification.json'):raise ValueError('inactive-word service receipt differs')
    if read(services/'run-result.json')['negative']['returncode']==0 or b'row result differs' not in (services/'negative.log').read_bytes():raise ValueError('active-row fault did not fail')
    full=a.runtime/'batch-programs-v1';records=[analyse(full,full/f'simulate-{i}.log',i) for i in range(4)]
    if read(full/'run-result.json')['negative']['returncode']==0 or b'resident M result mismatch' not in (full/'negative.log').read_bytes():raise ValueError('complete program row fault did not fail')
    prof=a.runtime/'batch-programs-v2-profile';observed=analyse(prof,prof/'simulate-2.log',2);m=read(prof/'manifest.json');programs=read(prof/'programs.json')['programs']
    for case,stats in zip(m['cases'],observed['utilization']):
        events=programs[case['strategy']]['events'];terms=[e for e in events if e['op']=='ROW_M_TERM']
        expected_cycles=sum(e['rows']*9 for e in terms);expected_slots=sum(e['rows']*e['k']*9 for e in terms)
        if (stats['issue_cycles'],stats['active_digit_slots'])!=(expected_cycles,expected_slots):raise ValueError('passive digit counters differ from actual unchanged native work')
    ir=read(a.ir);checked=[]
    for file in (a.runtime/'masked-v209-r2-width2/programs.json',a.server_programs):
        data=read(file);tile=data['tile'];count=0
        for fixture in data['fixtures']:
            values={(name,i):v for name,i,v in fixture['inputs']}
            for name,program in data['programs'].items():
                result=replay(tile,program,values);gold=result['observed_native_outputs'];count+=1
                for rr,g in enumerate(tile['graphs']):
                    for primitive,v in reference(ir['primitive_program'],g,values).items():
                        word=gold[tile['graph']['primitive_outputs'][f'{rr}:{primitive}']]&0xffffffff
                        if (word-(1<<32) if word&(1<<31) else word)!=v:raise ValueError('masked program differs from original integer graph')
        checked.append({'file':str(file),'independent_numeric_traces':count,'plans':len(data['programs'])})
    result={'passed':True,'services':q['proof'],'complete_RTL_programs_per_initialization':[r['cases'] for r in records],
        'complete_RTL_manifest_sha256':records[0]['manifest_sha256'],'passive_programs':observed['cases'],
        'passive_issue_fraction':observed['utilization'][0]['active_digit_slots']/observed['utilization'][0]['issue_capacity'],
        'numeric':checked,'scope':'unchanged native services and full cold row programs, synthetic edges/random only; actual weights/whole-loop/SystemC/energy/token/s excluded'}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
