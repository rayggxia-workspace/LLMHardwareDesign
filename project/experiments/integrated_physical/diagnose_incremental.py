"""Read-only evidence for actual empty dirty batches and unlogged changed nets."""
import argparse,re
from common import *
from incremental_audit import read_graph
from receive_physical import block,def_name
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);m=artifacts(a.stage);previous=Path(m['previous_directory']);artifacts(previous);b,bl,bs=read_graph(previous);c,cl,cs=read_graph(a.stage);log=block((a.stage/'flow.log').read_text(),'BEGIN_INCREMENTAL_CHANGE_INTERVAL','END_INCREMENTAL_CHANGE_INTERVAL');batches=[]
for line in log.splitlines():
 q=re.fullmatch(r'\[DEBUG GRT-incr\] (.*)',line)
 if q:
  if q[1]=='Dirty nets:':batches.append([])
  else:batches[-1].append(def_name(q[1].strip()))
dirty={n for x in batches for n in x};created=set(c)-set(b);changed={n for n in set(b)&set(c)if b[n]!=c[n]};missing=(created|changed)-dirty;rows=[]
for n in sorted(missing):rows.append({'net':n,'created':n in created,'before_pins':sorted(b.get(n,[])),'after_pins':sorted(c[n]),'before_segments':bs.get(n),'after_segments':cs.get(n),'before_locations':{owner:bl.get(owner)for owner,pin in b.get(n,[])if owner!='PIN'},'after_locations':{owner:cl.get(owner)for owner,pin in c[n]if owner!='PIN'}})
put(a.out/'diagnosis.json',{'source':sources(),'stage_manifest_sha256':sha(a.stage/'manifest.json'),'status':'READONLY_INCREMENTAL_LOG_AND_PHYSICAL_DIAGNOSIS','batch_count':len(batches),'empty_batch_indices':[i for i,x in enumerate(batches)if not x],'dirty_count':len(dirty),'new_nets':len(created),'reconnected_nets':len(changed),'unlogged_created_or_reconnected':rows});print('READONLY_INCREMENTAL_LOG_AND_PHYSICAL_DIAGNOSIS')
