"""Independent work/capacity and tail/ACK checks; NOT tensor numerical or RTL validation."""
from pathlib import Path
import json,math,subprocess
from audit_results import workload

def check_work(r):
 ts,ops,tokens=workload(Path('generated')/(r['workload']+'.trace'))
 profile=r['profile'];coal='coalesce' in profile;partial='partial' in profile
 chunk=int(profile.rsplit('_k',1)[1]) if '_k' in profile else 256
 tiles=minimum=outputs=0;peak=0
 for o in ops:
  if o['kind']!='Dot':continue
  abits=ts[o['inputs'][0]][2];bbits=8 if o['layout']==0 else ts[o['inputs'][1]][2]
  if o['layout']==0:minimum+=o['batches']*math.ceil(o['r']/8)*o['n']*o['k']*(bbits//8)
  outputs+=o['batches']*o['r']*o['n']
  for rr in range(0,o['r'],8):
   rows=min(8,o['r']-rr);workspace=1024+rows*8*12+int(coal)*rows*64
   available=16384-workspace
   kmax=min(chunk,max(8,(available//(2*(rows*(abits//8)+8*(bbits//8)))//8)*8))
   full_a=rows*o['k']*(abits//8)
   if full_a<available:
    rmax=((available-full_a)//(2*8*(bbits//8))//8)*8
    if rmax>=8:kmax=min(kmax,rmax)
   tiles+=o['batches']*math.ceil(o['n']/8)*math.ceil(o['k']/kmax)
 assert tiles==r['M_tiles']==r['M_commands'],(profile,tiles,r['M_tiles'])
 assert r['logical_read_bytes']>=minimum
 assert r['read_bus_bytes']>=r['logical_read_bytes']
 assert r['write_bus_bytes']>=r['logical_write_bytes']
 assert r['P_scratch_peak_bytes']<=16384
 assert r['U_cache_peak_bytes']+4096<=16384
 assert r['max_outstanding_beats']<=32 and r['max_outstanding_descriptors']<=32
 assert r['KV_state_write_bytes']==73728 if r['workload'].startswith('decode') else r['KV_state_write_bytes']==0
 assert abs(r['tokens_per_second']*r['seconds']-tokens)<1e-8
 assert abs(sum(r['spans_ticks'].values())-r['ticks'])<=len(r['spans_ticks'])
 for port in ('P0_S_busy_ticks','P1_S_busy_ticks'):
  if port in r:assert r[port]<=r['ticks']
 return dict(workload=r['workload'],profile=profile,M_tiles=tiles,static_weight_bytes_minimum=minimum,matrix_output_elements=outputs)

def run_small(name,trace,profile,fail=False):
 path=Path('generated/check-'+name+'.trace');path.write_text(trace)
 p=subprocess.run([str(Path('model.exe').resolve()),str(path),profile],capture_output=True,text=True)
 Path('generated/check-'+name+'-'+profile+'.log').write_text(p.stdout+p.stderr)
 if fail:
  assert p.returncode and 'read before producer write/ACK' in p.stdout+p.stderr
  return
 assert not p.returncode,(name,profile,p.stdout,p.stderr)
 r=json.loads(next(x[7:] for x in p.stdout.splitlines() if x.startswith('RESULT ')))
 assert r['P_scratch_peak_bytes']<=16384 and r['max_outstanding_beats']<=32
 assert r['logical_write_bytes']==int(trace.splitlines()[0].split()[-1])*4

def main():
 rows=[]
 for file in ['results.json','round2.json','final.json','fixed-k.json']:
  for r in json.loads(Path('generated',file).read_text()):rows.append(check_work(r))
 # Independently construct the actual per-cycle round-robin issue sequence.
 schedules=0
 for packets in range(1,17):
  for micro in [1,3,41,128]:
   ready=[0]*packets;cursor=0;last=0
   for _ in range(micro):
    for packet in range(packets):
     issue=max(cursor,ready[packet]);ready[packet]=issue+6;cursor=issue+1;last=max(last,issue+6)
   formula=(micro-1)*max(packets,6)+packets+5
   assert last==formula
   schedules+=1
 # Runtime coverage tracks each matrix output and marks it only after its
 # external write ACK. Odd N, uneven ownership and new row/batch transitions.
 profiles=['queued_pipe_w8','gap_packet_partial_coalesce_sched_k512','gap_dma_partial_coalesce_sched_k256']
 shapes=[(1,1,1),(1,9,13),(2,17,128),(9,24,129),(9,48,1025),(8,31,257)]
 checks=0
 for row,n,k in shapes:
  trace=f'3 1 {row*n}\n0 {row*k} 32 1\n1 {k*n} 16 1\n2 {row*n} 32 0\n2 Dot {row*n} {row} {n} {k} 1 16 0 2 0 1\n'
  for profile in profiles:run_small(f'matrix-{row}-{n}-{k}',trace,profile);checks+=1
 for profile in profiles:
  run_small('absent-producer','2 1 1\n0 4 32 0\n1 4 32 0\n1 Convert 4 1 4 1 1 0 0 1 0\n',profile,True);checks+=1
 report=dict(scope=__doc__,full_model_work_audits=rows,scoreboard_schedules=schedules,runtime_tail_negative_checks=checks)
 Path('generated/change-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('CHANGES_PASS',len(rows),'work audits;',schedules,'scoreboard schedules;',checks,'runtime checks')

if __name__=='__main__':main()
