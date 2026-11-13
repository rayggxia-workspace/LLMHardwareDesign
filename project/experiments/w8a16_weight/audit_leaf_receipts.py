"""Inspect recovered hashes and true event conservation; never simulate RTL locally."""
import argparse,collections,hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--receipts',type=Path);p.add_argument('--scale-stages',type=int,choices=(1,3),default=1);p.add_argument('--head-ii1',action='store_true');p.add_argument('--dispatch-prepare',type=int,choices=(0,1),default=0);p.add_argument('--expected-faults',type=int,default=6);a=p.parse_args();r=a.receipts if a.receipts is not None else a.run/'receipts'
 assert not a.head_ii1 or a.scale_stages==3
 manifest=json.loads((r/'receipts-manifest.json').read_text())
 for name,digest in manifest.items():assert sha(r/name)==digest,name
 for line in(r/'source.sha256').read_text().splitlines():
  digest,name=line.split('  ',1);assert sha(r/'source'/name)==digest
 oracle=json.loads((r/'vectors/manifest.json').read_text());assert oracle['passed']and oracle['full_model_SHA256_checked'];assert sha(r/'vectors/records.txt')==oracle['fixture_SHA256']
 rows=[]
 for seed in range(25011,25017):
  folder=r/f'leaf-seed-{seed}';result=json.loads((folder/'result.json').read_text());assert result['passed']and len(result['runs'])==3
  lint=(folder/'lint.log').read_text();assert '%Warning'not in lint and '%Error'not in lint
  for initial in(0,1,2):
   log=(folder/f'initial-{initial}.log').read_text().strip();assert log==result['runs'][initial]['receipt']and log.startswith('PASS leaf ')
   events=[line.split(',')for line in(folder/f'timing-{initial}.csv').read_text().splitlines()]
   req=collections.Counter((int(e[2]),int(e[3]))for e in events if e[0]=='MC_REQ')
   ret=collections.Counter((int(e[2]),int(e[3]))for e in events if e[0]=='MC_RETURN'and e[4]=='0')
   assert req==ret and all(n==1 for n in req.values()),'real DMA work conservation'
   responses=[e for e in events if e[0]=='RESPONSE'];snapshots={int(e[3])for e in responses if e[2]=='4'and e[6]=='4'}
   writes=collections.Counter((int(e[2]),int(e[3]))for e in events if e[0]=='S_REQ')
   assert writes==collections.Counter({(ticket,word):1 for ticket in snapshots for word in(0,1)}),'RF-only record wrote S / snapshot missed word'
   assert sum(e[0]=='S_ACK'for e in events)==len(writes)
   assert sum(e[2]=='7'for e in responses)==a.expected_faults
   a_by_record=collections.Counter(int(e[2])for e in events if e[0]=='A')
   aborted={int(e[2]):int(e[3])for e in events if e[0]=='ABORT_PARTIAL'}
   for rid,v in a_by_record.items():assert v==aborted.get(rid,8)
   for rid,count in aborted.items():
    assert count==3 and a_by_record[rid]==3 and any(e[2]=='5'and int(e[4])==rid for e in responses)
    assert not any(e[2]in('3','4')and int(e[4])==rid for e in responses), 'abort fabricated normal completion'
   core={int(e[2]):int(e[1])for e in events if e[0]=='CORE_EXEC'}
   input_eop={int(e[3]):int(e[1])for e in responses if e[2]=='3'}
   rf_eop={int(e[3]):int(e[1])for e in responses if e[2]=='4'}
   costs={}
   for rid in(5000,5001,5010,5011):
    er=next(e for e in responses if e[2]=='4'and int(e[4])==rid);sid=int(er[3]);costs[rid]=dict(core_to_input_EOP=input_eop[sid]-core[sid],core_to_RF_EOP=rf_eop[sid]-core[sid],RF_flits=int(er[6]))
    expected_input=19 if a.scale_stages==3 and rid==5001 and not a.head_ii1 else 11
    expected_RF=(32 if rid==5001 and not a.head_ii1 else 16 if rid==5010 else 18)if a.scale_stages==3 else(14 if rid==5010 else 16)
    assert costs[rid]['core_to_input_EOP']==expected_input
    assert costs[rid]['core_to_RF_EOP']==expected_RF
   if any(e[2]=='4'and e[4]=='5020'for e in responses):
    assert a.scale_stages==3,'head continuation fixture requires its measured pipeline profile'
    head_sessions=[]
    for rid,rf_cost in((5020,16 if a.head_ii1 else 30),(5021,18 if a.head_ii1 else 32)):
     er=next(e for e in responses if e[2]=='4'and int(e[4])==rid);sid=int(er[3]);head_sessions.append(sid)
     costs[rid]=dict(core_to_input_EOP=input_eop[sid]-core[sid],core_to_RF_EOP=rf_eop[sid]-core[sid],RF_flits=int(er[6]))
     assert costs[rid]['core_to_input_EOP']==(11 if a.head_ii1 else 19)and costs[rid]['core_to_RF_EOP']==rf_cost
    assert core[head_sessions[1]]-core[head_sessions[0]]==(21 if a.head_ii1 else 35)+a.dispatch_prepare,'actual guard and product framing initiation interval'
   rows.append(dict(seed=seed,initial=initial,MC64beats=len(req),A32beats=sum(a_by_record.values()),RF_snapshots=len(snapshots),S128ACKs=len(writes),faults=a.expected_faults,isolated_product_costs=costs))
 summary=dict(passed=True,dispatch_prepare_cycles=a.dispatch_prepare,scale_pipeline_stages=a.scale_stages,head_STEP_II1=a.head_ii1,source_commit=(r/'source/source-commit.txt').read_text().strip(),files_checked=len(manifest),model_SHA256=oracle['model_SHA256'],fixture_SHA256=oracle['fixture_SHA256'],runs=rows,scope='Recovered artifact hash/event audit only; verifies physical-port test receipt work conservation, no local execution of RTL or new numerical experiment. S provider host RTT2 ideal / random3..9, actual guard RTL; not complete system or postroute acceptance.')
 (a.run/'audit.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(dict(passed=True,runs=len(rows),files_checked=len(manifest),isolated_costs=rows[0]['isolated_product_costs'])))
if __name__=='__main__':main()
