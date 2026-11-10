"""Independent receipt hashes, source conservation, strict issue-window audit."""
import argparse,collections,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--receipts',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.receipts;manifest=json.loads((r/'receipts-manifest.json').read_text())
 for name,digest in manifest.items():assert sha(r/name)==digest,name
 for line in(r/'source.sha256').read_text().splitlines():
  digest,name=line.split('  ',1);assert sha(r/'source'/name)==digest
 rows=[];performance=[]
 for seed in range(25021,25027):
  for limit in(65535,3):
   folder=r/f'seed-{seed}-limit-{limit}';result=json.loads((folder/'result.json').read_text());assert result['passed']and result['serial_limit']==limit and len(result['runs'])==3
   assert '%Warning'not in(folder/'lint.log').read_text()
   for initial in(0,1,2):
    assert(folder/f'initial-{initial}.log').read_text().strip()==result['runs'][initial]['receipt']
    events=[line.split(',')for line in(folder/f'timing-{initial}.csv').read_text().splitlines()];accepted=collections.Counter();returned=collections.Counter();issued=collections.Counter();cancelled=collections.Counter();abandoned=collections.Counter();purged=collections.Counter();perch=[collections.Counter(),collections.Counter()];live=set();fences=0;perf_begin=None
    for e in events:
     if e[0]=='RESERVE':key=(int(e[2]),int(e[3]));accepted[key]+=1;assert key not in live;live.add(key)
     elif e[0]=='CLIENT_RETURN':key=(int(e[2]),int(e[3]));returned[key]+=1;assert key in live;live.remove(key)
     elif e[0]=='RESET_ABANDON':key=(int(e[2]),int(e[3]));abandoned[key]+=1;assert key in live;live.remove(key)
     elif e[0]=='PURGE_DROP':key=(int(e[2]),int(e[3]));purged[key]+=1;assert abandoned[key]==1
     elif e[0]=='CANCEL_ACK'and e[4]=='0':key=(int(e[2]),int(e[3]));cancelled[key]+=1;assert key in live;live.remove(key)
     elif e[0]=='ISSUE':key=(int(e[2]),int(e[3]));assert key in live;issued[key]+=1;perch[int(e[4])//2][int(e[1])]+=1
     elif e[0]=='FENCE_OFFER':assert not live,'purge before source/real return/cancel drain';fences+=1
     elif e[0]=='PERF_BEGIN':perf_begin=int(e[1])
     elif e[0]=='PERF_WINDOW':
      ch,first,last,count=int(e[1]),int(e[2]),int(e[3]),int(e[4]);measured=float(e[5]);purges=int(e[6]);actual=sum(n for cy,n in perch[ch].items()if first<=cy<=last);seq=sorted(cy for cy,n in perch[ch].items()for _ in range(n)if cy>=perf_begin);assert seq[100]==first and seq[-101]==last and len(seq)-200==count;assert count<=actual<=count+2
      efficiency=count*3/(4*(last-first+1));assert abs(efficiency-measured)<5e-6
      if purges==0:assert efficiency>.97
      performance.append(dict(seed=seed,initial=initial,serial_limit=limit,channel=ch,first_cycle=first,last_cycle=last,trimmed_real_issue_count=count,whole_boundary_cycles_real_issues=actual,service_efficiency=efficiency,whole_cycle_service_efficiency=actual*3/(4*(last-first+1)),real_purges=purges))
    assert not live and accepted==returned+cancelled+abandoned and issued==returned+purged
    assert all(n==1 for n in accepted.values())
    for series in perch:
     for cycle in range(max(series)+1):assert series[cycle]<=2 and sum(series[x]for x in(cycle,cycle-1,cycle-2))<=4
    rows.append(dict(seed=seed,initial=initial,serial_limit=limit,accepted=sum(accepted.values()),DDR_issued=sum(issued.values()),client_returns=sum(returned.values()),reserved_cancelled=sum(cancelled.values()),reset_abandoned=sum(abandoned.values()),actual_purge_discarded=sum(purged.values()),real_backend_fences=fences,strict_rolling3_verified=True))
 result=dict(passed=True,source_commit=(r/'source/source-commit.txt').read_text().strip(),files_checked=len(manifest),runs=rows,service_windows=performance,scope='Local immutable receipt/hash/event audit only; actual RTL execution occurred on Slurm. No SystemC/full-model/physical claim.')
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,runs=len(rows),files_checked=len(manifest),first=rows[0])))
if __name__=='__main__':main()
