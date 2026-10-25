"""Final evidence index and measured counter summary; never extrapolate end-to-end model PPA."""
import argparse,json,hashlib,os,platform,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);b=json.loads((ROOT/'binding.json').read_text())
 for n,h in b['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('frozen analysis source')
 receipts=[]
 for name in ('receive07s0','receive07s1','gatereceive02'):
  f=a.root/name/'receipt.json';r=json.loads(f.read_text());expected='PASS97_EXACT_MAPPED_GATE_AND_ORIGINAL_ORACLE'if name=='gatereceive02'else'PASS_ORIGINAL_V_M_NORM_AND_RECOVERY'
  if r['status']!=expected:raise ValueError('accepted evidence required '+name)
  receipts.append({'directory':name,'receipt_sha256':sha(f),'status':r['status'],'rows':len(r['rows'])})
 cost=json.loads((a.root/'cost02.json').read_text());rows=[];protocols=[]
 for s in (0,1):
  r=json.loads((a.root/f'receive07s{s}'/'receipt.json').read_text());protocols.append(dict(r['protocol'],stall=s));rows += [dict(x,stall=s,external_line_bytes=x['transactions']*16,modeled_wire_bytes=x['wire_beats']*16,unattributed_M_and_handoff_cycles=x['cycles']-x['v_cycles']-x['norm_cycles'])for x in r['rows']if x['role']=='mixed']
 result={'status':'PASS97_BOUNDED_FULL_CONSUMER_EVIDENCE','analysis_source':b,'receipts':receipts,'cost':cost,'cost_sha256':sha(a.root/'cost02.json'),'formal_rows':rows,'protocols':protocols,'numeric_boundary_deltas':r['numeric_boundary_deltas'],'real_deltas':r['delta_by_real_case'],'environment':{'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),'hostname':platform.node(),'affinity_cpus':len(os.sched_getaffinity(0)),'slurm_job':os.environ.get('SLURM_JOB_ID')},'limits':['The original74 oracle checks bounded integer reference equivalence, not FP model quality or full model execution.','Dedicated V front and bounded K512/8expert/H1536 M are real hardware; general80V ISA, attention A, recurrent R, generalD/multi-context compiler and full library remain unqualified.','Counters include actual V external lookup/line access and shared M/norm work. Wire beats exclude physical tag-sideband/fabric/clock and ROM macro costs.','Gate: selected8 outputs in4runs, no direct output Q injection, no RTL50command error/abort qualification at gate level. Behavioral SRAM, zero delay.','Logic-only mapped area includes new V RNE/abs/compare/address/control/line registers; no SRAM/ROM macros, CTS, placed wire RC, signoff PVT or guaranteed Fmax.','No speedup vs93 is asserted:97 adds computation and uses a dedicated frontend/resident M profile; cross-batch mapping differences are not a controlled incremental-area experiment.']};(a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'rows':len(rows),'cost':cost['area_um2_logic_only'],'receipts':receipts}))
if __name__=='__main__':main()
