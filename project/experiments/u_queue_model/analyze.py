"""Independent receipt/log/control recheck; does not run simulation locally."""
import argparse,json,math,re,sys
from pathlib import Path
from run import check
from profile import sha,require
def collect(root):
    c=json.loads((root/'collection.json').read_bytes())
    for n,d in c['files'].items():require(sha(root/n)==d['sha256'],'receipt drift '+n)
    r=json.loads((root/'results/result.json').read_bytes());require(r['passed'],'failed run')
    return r,len(c['files'])
def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    native,nc=collect(a.native);model,mc=collect(a.model);prior=json.loads(a.prior.read_bytes())
    require(sha(a.prior)=='59e272db682fff06f01d0f3ef170b9c93da24ca9d0a2d73338a366a8d1b017ec','frozen reference identity')
    runs=sum(len(v['runs']) for v in native['tests'].values());require(runs==195 and native['default_exact_pairs']==27,'native gates')
    for left,right in zip(native['tests']['reference']['runs'],native['tests']['q0p0']['runs']):
        require(left['case']==right['case'] and left['mode']==right['mode'] and left['seed']==right['seed'],'default pairing')
        require(left['measurements']==right['measurements'] and left['checks']==right['checks'],'default observation drift')
    for test in native['tests'].values():
        require(test['passed'],'native test failure')
        for run in test['runs']:
            path=a.native/'results'/run['summary'];require(sha(path)==run['summary_sha256'],'native summary drift')
            prefix='REGION_MEASURE ' if 'tiles' in run else 'QUEUE_MEASURE '
            rows=[{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',s)} for s in path.read_text().splitlines() if s.startswith(prefix)]
            require(rows==[run['measurements']],'native summary mismatch')
    rows=[];fullcontrols=0;negative=0
    for c in model['cases']:
        name=c['case'];refname=name if name in ['base','s16_measured'] else 's16_measured'
        ref=next(x['result'] for x in prior['cases'] if x['case']==refname and all(x[k]==c[k] for k in ['workload','profile','dual_ports']))
        result=c['result'];audit=check(result,ref,name,c['workload']);require(audit==c['audit'],'model audit drift')
        log=a.model/'results'/c['log'];require(sha(log)==c['log_sha256'],'model log drift')
        actual=[json.loads(l[7:]) for l in log.read_text().splitlines() if l.startswith('RESULT ')];require(actual==[result],'model log RESULT mismatch')
        fullcontrols+=audit['baseline_exact'];negative+=len(c['negative_checks'])
        rows.append(dict(case=name,workload=c['workload'],profile=c['profile'],dual_ports=c['dual_ports'],tokens_per_second=result['tokens_per_second'],
                         ticks=result['ticks'],region=result['optimization_sweep']['native_region']))
    require(len(rows)==40 and fullcontrols==16 and negative==200,'model coverage')
    queue=[]
    for case in ['unary_s16','binary_s16','ternary_s16','narrow_s32','mixed_edges','hazards','direct','backpressure','io_contention']:
        cycles={}
        for depth in [0,2,4]:
            test=native['tests'][f'q{depth}p0'];run=next(x for x in test['runs'] if x['mode']==1 and x['case']==case)
            cycles[str(depth)]=run['measurements']['cycles']
        queue.append(dict(case=case,cycles=cycles,q2_gain_percent=(cycles['0']/cycles['2']-1)*100,q4_gain_percent=(cycles['0']/cycles['4']-1)*100))
    area={k:v['standard_cell_um2'] for k,v in native['area']['modules'].items()}
    baseline=area['front_serial']+area['e_legacy']
    increments={f'q{d}':dict(front_delta_mm2=(area[f'front_q{d}']-area['front_serial'])/1e6,
        front_and_region_delta_mm2=(area[f'front_q{d}']-area['front_serial']+area['region'])/1e6,
        front_plus_E_increase_percent=(area[f'front_q{d}']-area['front_serial'])/baseline*100) for d in [2,4]}
    r=dict(passed=True,native_runs=runs,native_default_exact_pairs=27,model_cases=40,model_full_controls=fullcontrols,negative_checks=negative,
        received_files=dict(native=nc,model=mc),native_source=native['source_commit'],model_source=model['source_commit'],
        native_result_sha256=sha(a.native/'results/result.json'),model_result_sha256=sha(a.model/'results/result.json'),
        queue=queue,area_um2=area,area_increments=increments,model=rows,full_model_RTL_calibrated=False,actual_model_values_verified=False,
        trace_E_eligible={k:v['eligible_pure_S16_E'] for k,v in native['generation']['trace_audit'].items()})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['passed','native_runs','model_cases','model_full_controls','negative_checks','received_files','area_increments']}))
if __name__=='__main__':main()
