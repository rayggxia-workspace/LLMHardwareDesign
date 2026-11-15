"""Bounded, diverse retention without dominance across incompatible chip states."""
import json

def pressure(label,capacities):
 counts={owner:sum(v['dirty'] for v in pages.values())*32
         for owner,pages in label['state']['memory'].items()}
 return (max((words/capacities[o] for o,words in counts.items()),default=0),sum(counts.values()))

def retain(labels,width,capacities):
 if width<3:raise ValueError('diverse beam needs at least three slots')
 time=lambda s:s['time']+s['remaining']/max(1,len(capacities))
 traffic=lambda s:s['bytes']+s['remaining_bytes']
 rankings=[
  sorted(labels,key=lambda s:(time(s),traffic(s),pressure(s,capacities))),
  sorted(labels,key=lambda s:(traffic(s),time(s),pressure(s,capacities))),
  sorted(labels,key=lambda s:(pressure(s,capacities),time(s),traffic(s)))]
 chosen=[];seen=set();indices=[0,0,0]
 while len(chosen)<width:
  added=False
  for k,rows in enumerate(rankings):
   while indices[k]<len(rows):
    label=rows[indices[k]];indices[k]+=1
    # Exact equivalence only. Different mappings, buffers, readiness, times or
    # backed copies must not be discarded merely for sharing an operator count.
    key=json.dumps({n:v for n,v in label.items() if n not in ('history','handoff_priority','ready_resident_credit')},
                   sort_keys=True,separators=(',',':'))
    if key in seen:continue
    seen.add(key);chosen.append(label);added=True;break
   if len(chosen)==width:break
  if not added:break
 return chosen
