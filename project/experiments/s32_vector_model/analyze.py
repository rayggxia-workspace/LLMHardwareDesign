"""Recheck receipts and logged results without running EDA locally."""
import argparse,json,re
from pathlib import Path
from profile import sha,require
from run import check

def collect(root):
 c=json.loads((root/'collection.json').read_bytes())
 for n,d in c['files'].items():require(sha(root/n)==d['sha256'],'receipt drift '+n)
 r=json.loads((root/'results/result.json').read_bytes());require(r['passed'],'failed run')
 return r,len(c['files'])

def main():
 p=argparse.ArgumentParser()
 for n in ['native','model','prior','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();native,nc=collect(a.native);model,mc=collect(a.model);prior=json.loads(a.prior.read_bytes())
 require(sha(a.prior)=='4be10c512c8d28e7e41eaaedab4a4f6803adbc4450458f0ec59f33c49b20c1cc','prior identity')
 runs=sum(len(v['runs']) for v in native['tests'].values());require(runs==186 and native['default_exact_pairs']==27,'native gates')
 for left,right in zip(native['tests']['reference']['runs'],native['tests']['legacy0']['runs']):
  require(all(left[k]==right[k] for k in ['case','mode','seed','measurements','checks']),'default changed')
 for test in native['tests'].values():
  require(test['passed'],'test failure')
  for r in test['runs']:
   f=a.native/'results'/r['summary'];require(sha(f)==r['summary_sha256'],'summary hash')
   prefix='REGION_MEASURE ' if 'tiles' in r else 'QUEUE_MEASURE '
   rows=[{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',s)} for s in f.read_text().splitlines() if s.startswith(prefix)]
   require(rows==[r['measurements']],'summary mismatch')
 rows=[];controls=negative=0
 for c in model['cases']:
  ref=next(x['result'] for x in prior['cases'] if x['case']=='region_q2' and all(x[k]==c[k] for k in ['workload','profile','dual_ports']))
  r=c['result'];audit=check(r,ref,c['case'],c['workload'],model['profile']);require(audit==c['audit'],'audit mismatch')
  log=a.model/'results'/c['log'];require(sha(log)==c['log_sha256'],'log hash')
  require([json.loads(s[7:]) for s in log.read_text().splitlines() if s.startswith('RESULT ')]==[r],'logged result mismatch')
  controls+=audit['baseline_exact'];negative+=len(c['negative_checks'])
  rows.append(dict(case=c['case'],workload=c['workload'],profile=c['profile'],dual_ports=c['dual_ports'],tokens_per_second=r['tokens_per_second'],ticks=r['ticks'],native_E32=r['native_E32'],spans_ticks=r['spans_ticks']))
 require(len(rows)==32 and controls==8 and negative==160,'model coverage')
 queue=[]
 for case in [v['name'] for v in native['generation']['cases']]:
  cycles={str(d):next(x['measurements']['cycles'] for x in native['tests']['s32q'+str(d)]['runs'] if x['mode']==1 and x['case']==case) for d in [0,2,4]}
  queue.append(dict(case=case,cycles=cycles,q2_gain_percent=(cycles['0']/cycles['2']-1)*100,q4_gain_percent=(cycles['0']/cycles['4']-1)*100))
 area={k:v['standard_cell_um2'] for k,v in native['area']['modules'].items()};require(len(area)==8 and native['area']['status']=='passed','area gates')
 inc=dict(core_delta_mm2=(area['e_s32']-area['e_legacy'])/1e6,core_increase_percent=(area['e_s32']/area['e_legacy']-1)*100,
  s32q2_vs_s16q2_delta_mm2=(area['e_s32']+area['front_s32q2']-area['e_legacy']-area['front_q2'])/1e6,
  s32q2_vs_s16serial_delta_mm2=(area['e_s32']+area['front_s32q2']-area['e_legacy']-area['front_serial'])/1e6)
 result=dict(passed=True,native_runs=runs,model_cases=len(rows),full_controls=controls,negative_checks=negative,received_files=dict(native=nc,model=mc),
  native_result_sha256=sha(a.native/'results/result.json'),model_result_sha256=sha(a.model/'results/result.json'),native_source=native['source_commit'],model_source=model['source_commit'],
  queue=queue,area_um2=area,area_increments=inc,model=rows,full_model_RTL_calibrated=False,actual_model_values_verified=False)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['passed','native_runs','model_cases','full_controls','negative_checks','received_files','area_increments']}))
if __name__=='__main__':main()
