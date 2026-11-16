"""Independent full-source replay, source cover and actual RTL receipts."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_lane_cover import verify
from resident_batch_graph import digest
from resident_batch_probe import analyse
from resident_survey import reference
from verify_resident_batch import replay


def main():
    p=argparse.ArgumentParser()
    for n in ('runtime23','runtime24','server23','ir','output'):p.add_argument(n,type=Path)
    p.add_argument('--server24',type=Path)
    a=p.parse_args();read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    lane=read(a.runtime24/'lane-enriched.json');verify(lane['tile']);ir=read(a.ir)
    pools=[read(a.runtime23/'scatter-r2-width2/programs.json'),read(a.server23/'generated/programs.json'),lane]
    if a.server24:pools.append(read(a.server24/'generated/programs.json'))
    original=lane['tile']['operand_cover']['source_tile'];plan_ticks={};counts=[]
    for i,data in enumerate(pools):
        if i<2 and digest(data['tile'])!=digest(original):raise ValueError('baseline source differs')
        if i>=2 and digest(data['tile'])!=digest(lane['tile']):raise ValueError('covered source differs')
        count=0
        for fixture in lane['fixtures']:
            values={(t,j):v for t,j,v in fixture['inputs']}
            for name,program in data['programs'].items():
                result=replay(data['tile'],program,values);seen=result['observed_native_outputs'];count+=1
                for rr,g in enumerate(original['graphs']):
                    for primitive,value in reference(ir['primitive_program'],g,values).items():
                        word=seen[data['tile']['graph']['primitive_outputs'][f'{rr}:{primitive}']]&0xffffffff
                        if (word-(1<<32) if word&(1<<31) else word)!=value:raise ValueError('implementation differs from original program')
                plan_ticks[f'{i}:{name}']=program['total_ticks']
        counts.append(count)
    rtl=a.runtime24/'lane-programs-v2';records=[analyse(rtl,rtl/f'simulate-{i}.log',i) for i in range(4)]
    neg=read(rtl/'run-result.json')['negative'];wrong_k=read(rtl/'negative-k-result.json')
    if neg['returncode']==0 or b'resident M result mismatch' not in (rtl/'negative.log').read_bytes():raise ValueError('wrong-row fault not detected')
    if wrong_k['returncode']==0 or not wrong_k['actual_K_fault'] or not wrong_k['numeric_failure']:raise ValueError('wrong-K fault not detected')
    baseline={k:t for k,t in plan_ticks.items() if k.split(':')[0] in ('0','1')};new={k:t for k,t in plan_ticks.items() if k.split(':')[0] not in ('0','1')}
    prior_greedy=min(t for k,t in baseline.items() if 'greedy' in k);new_greedy=min(t for k,t in new.items() if 'greedy' in k)
    new_dp=min(t for k,t in new.items() if 'dp' in k)
    oldrtl=a.runtime23/'scatter-programs-v1';oldrecords=[analyse(oldrtl,oldrtl/f'simulate-{i}.log',i) for i in range(4)]
    if read(oldrtl/'run-result.json')['negative']['returncode']==0:raise ValueError('old scatter negative did not fail')
    if b'PASS native resident record programs' not in (a.runtime24/'lane-programs-v1/negative.log').read_bytes():raise ValueError('first failed fault control was not preserved')
    profile=records[0]['utilization'][0]
    result={'passed':True,'numeric_traces_per_pool':counts,'heterogeneous_fixtures':len(lane['fixtures']),
        'scatter_RTL_programs_per_initialization':[r['cases'] for r in oldrecords],
        'complete_RTL_programs_per_initialization':[r['cases'] for r in records],
        'RTL_manifest_sha256':records[0]['manifest_sha256'],'actual_wrong_row_returncode':neg['returncode'],
        'actual_wrong_K_returncode':wrong_k['returncode'],'prior_strong_greedy_ticks':prior_greedy,
        'prior_best_verified_ticks':min(baseline.values()),'new_strong_greedy_ticks':new_greedy,'new_best_DP_ticks':new_dp,
        'cover_vs_prior_strong_greedy_fraction':1-min(new.values())/prior_greedy,
        'new_DP_vs_new_strong_greedy_fraction':1-new_dp/new_greedy,
        'first_lane_probe_badrow_control':'not detected; preserved, replaced by heterogeneous v2',
        'passive_issue_cycles':profile['issue_cycles'],'passive_active_slots':profile['active_digit_slots'],
        'passive_issue_capacity':profile['issue_capacity'],
        'scope':'source-bound dynamic cover, 7 synthetic inputs and complete native programs; no new actual-weight/loop/full-model/SystemC/DRAM/energy/token/s qualification'}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
