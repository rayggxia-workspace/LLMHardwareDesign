"""Independently re-audit the saved round17 programs and evidence scopes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from resident_replay import replay
from verify_resident_continuation import verify
from transport_survey import check


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for name in ('runtime','ir','results','output'):p.add_argument(name,type=Path)
    a=p.parse_args();ir=read(a.ir);groups={}
    for r in ir['resident_recipes'].values():
        if r.get('continuation_loop'):groups.setdefault(tuple(r['primitives']),r)
    recipes=sorted(groups.values(),key=lambda r:len(r['graph']['operations']),reverse=True)
    sequences=cases=0
    for folder in ('initialization-v1','transport-v1','transport-v2'):
        files=list((a.runtime/folder).glob('region-*.json'))
        expected={'initialization-v1':72,'transport-v1':35,'transport-v2':12}[folder]
        if len(files)!=expected:raise ValueError('experiment saved-case count differs '+folder)
        for file in files:
            ri=int(re.match(r'region-(\d+)-',file.name).group(1));r=recipes[ri];seq=read(file)
            verify(r['graph'],r['loop'],seq,r['plan']['actors'],r['plan']['zero_address'],ir['resident_timing'])
            cases+=check(r,seq);sequences+=1
    if read(a.runtime/'transport-v1-exit.json')['returncode']!=3221225477:
        raise ValueError('original Windows abnormal exit evidence changed')
    if read(a.runtime/'transport-v1-recovery-exit.json')['returncode']!=0:raise ValueError('recovery not successful')
    recovered=read(a.runtime/'transport-v1-recovery/report.json')
    if recovered['frozen_source_sha256']!=read(a.runtime/'transport-v1-source/manifest.json')['files']:
        raise ValueError('recovery did not use original source snapshot')
    seq=read(a.runtime/'transport-v1-recovery/program.json');r=recipes[0]
    verify(r['graph'],r['loop'],seq,r['plan']['actors'],r['plan']['zero_address'],ir['resident_timing'])
    cases+=check(r,seq);sequences+=1
    for file in sorted((a.runtime/'topology-reference-v1').glob('case-*.json')):
        seq=read(file);verify(r['graph'],r['loop'],seq,r['plan']['actors'],r['plan']['zero_address'],ir['resident_timing'])
        cases+=check(r,seq);sequences+=1
    if read(a.runtime/'transport-v2-exit.json')['returncode'] or read(a.runtime/'initialization-v1-exit.json')['returncode']:
        raise ValueError('completed experiment failed')
    actual=a.runtime/'actual-boundaries-v1';report=read(actual/'report.json');programs=read(actual/'programs.json')
    fixtures=read(a.results/'resident-boundary-program-terminal-r16/generated/actual-boundary-fixtures.json')
    graphs=[g for row in read(a.results/'source-closed-pointwise-r14/generated/native-regions.json') for g in row['graphs']]
    actual_cases=0
    for f in fixtures:
        graph=graphs[f['region_index']];values={(n,i):v for n,i,v in f['inputs']};gold=execute(graph,values)
        for body in programs[str(f['region_index'])].values():
            result=replay(graph,body,values)
            if result['observed_native_outputs']!={n['output']:gold[n['output']] for n in graph['operations']}:
                raise ValueError('actual-value independent transport replay differs')
            actual_cases+=1
    if (actual_cases,len(fixtures))!=(report['program_replays'],report['actual_fixtures']):raise ValueError('actual-value extent differs')
    rtl=a.runtime/'transport-rtl-v1';acceptance=read(rtl/'acceptance.json')
    for relative,expected in acceptance['sha256'].items():
        if sha(rtl/relative)!=expected:raise ValueError('candidate RTL evidence changed '+relative)
    for mode in range(3):
        raw=(rtl/f'simulate-{mode}.log').read_bytes()
        # WSL may prefix its UTF16 diagnostic without an ASCII newline. Parse
        # the full ASCII record grammar; never rewrite the preserved raw log.
        rows=re.findall(rb'TRANSFER src=(\d+) dst=(\d+) reserve=(\d+) offer=(\d+) ack=(\d+) slots=(\d+)',raw)
        if len(rows)!=64 or b'transfers=64 commits=64 releases=64 min_slots=6 max_slots=6' not in raw:
            raise ValueError('RTL candidate transfer extent/profile differs')
        for i,row in enumerate(rows):
            src,dst,reserve,offer,ack,slots=map(int,row);case=i//2
            expected=(case*33%1024,1023-case*33%1024,0,0,0) if i%2==0 else (
                case*33%1024,1023-case*33%1024,3+case%5,2+case%3,4+case%7)
            if (src,dst,reserve,offer,ack)!=expected or i%2==0 and slots!=6:
                raise ValueError('RTL candidate individual record differs')
    if b'source release before destination ACK' not in (rtl/'negative-ack.log').read_bytes():
        raise ValueError('RTL candidate negative evidence missing')
    for platform in ('windows','linux'):
        if read(a.runtime/(platform+'-tests-v3-exit.json'))['returncode'] or b'Ran 277 tests' not in (a.runtime/(platform+'-tests-v3.log')).read_bytes():
            raise ValueError('full regression evidence differs '+platform)
    full=a.results/'resident-cover-full-terminal-r17';receipt=read(full/'receipt.json')
    for relative,entry in receipt['recovered'].items():
        if sha(full/relative)!=entry['sha256']:raise ValueError('collected full-search evidence changed')
    if b'101591|COMPLETED|0:0' not in (full/'slurm.psv').read_bytes():raise ValueError('full-search terminal evidence missing')
    full_summary=read(full/'generated/summary.json');v2=read(a.runtime/'transport-v2/summary.json');comparisons=[]
    for ri in range(2):
        rows=[x for x in v2['rows'] if x['region']==ri]
        baseline=min((x for x in rows if x['net_budget']==0),key=lambda x:x['total_ticks'])
        pair=min((x for x in rows if x['net_budget']==2),key=lambda x:x['total_ticks'])
        comparisons.append({'region':ri,'baseline_ticks':baseline['total_ticks'],'candidate_pair_ticks':pair['total_ticks'],
            'candidate_reduction_fraction':1-pair['total_ticks']/baseline['total_ticks'],
            'baseline_external_records':baseline['external_words'],'candidate_external_records':pair['external_words'],
            'candidate_record_reduction_fraction':1-pair['external_words']/baseline['external_words'],
            'strong_greedy_ticks':pair['total_ticks'],
            'dp_ticks':next(x['total_ticks'] for x in rows if x['net_budget']==2 and x['strategy']=='future_dp')})
    context={'recipes':[{'graph':r['graph'],'loop':r['loop'],'actors':r['plan']['actors'],'zero_address':r['plan']['zero_address']} for r in recipes[:2]],
             'timing':ir['resident_timing'],'source_program':ir['primitive_program'],
             'actual_graphs':graphs,'actual_fixtures':fixtures}
    (a.runtime/'input-context.json').write_text(json.dumps(context,separators=(',',':'))+'\n')
    result={'passed':True,'independently_checked_sequences':sequences,'synthetic_element_replays':cases,
            'actual_boundary_fixtures':len(fixtures),'actual_program_replays':actual_cases,
            'rtl_transfers_per_initialization':64,'rtl_initializations':3,'tests_per_environment':277,
            'full_search_plans':full_summary['plans'],'candidate_comparisons':comparisons,
            'ir_sha256':sha(a.ir),'qualification':'experimental candidate dataflow only, not qualified P/U paths or new full-model/system performance',
            'native_reuse_diagnostic':read(a.runtime/'native-reuse-v1/summary.json'),
            'original_failure':{'returncode':3221225477,'reason':'unverified; no Python traceback','completed_cases':35,
                                'failed_strategy_recovered_on_linux':True,'unstarted_region1_v1':'not executed; v2 explicitly separate'},
            'scope':'independent saved program/finite-S/accounting/actual-boundary/RTL-log/source-hash audit; controller/physical/SystemC/energy/token/s remain separate'}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('native_reuse_diagnostic','full_search_plans')}))


if __name__=='__main__':main()
