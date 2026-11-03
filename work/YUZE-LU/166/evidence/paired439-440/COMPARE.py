"""Reproduce the paired extracted slack decomposition from received raw reports."""
from pathlib import Path
import hashlib,json,re
B=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rec=json.loads((B/'RECEPTION.json').read_text());assert rec['all_original_bytes_received']and rec['qualified']is False
for name,row in rec['files'].items():assert sha(B/name)==row['sha256']and (B/name).stat().st_size==row['bytes']
def read(n):
 d=B/('attempt'+str(n))/'selected-paths';r=json.loads((d/'receipt.json').read_text());assert r['passed']
 rows={(x['startpoint'],x['endpoint']):x for x in r['rows']};out={}
 for block in(d/'selected-min.rpt').read_text().split('Startpoint: ')[1:]:
  start=block.splitlines()[0].strip();end=re.search(r'^Endpoint: (.+)$',block,re.M).group(1).strip();key=(start+'/Q',end+'/D');assert key in rows and key not in out
  clocks=[]
  for line in block.splitlines():
   m=re.match(r'^\s*([-+0-9.]+)\s+([-+0-9.]+)\s+[\^v]\s+(\S+)\s+\(',line)
   if m and m.group(3)in [start+'/CK',end+'/CK']:clocks.append((m.group(3),float(m.group(2))))
  assert len(clocks)==2 and clocks[0][0]==start+'/CK'and clocks[1][0]==end+'/CK'
  val=lambda text:float(re.search(r'^\s*([-+0-9.]+)\s+'+text,block,re.M).group(1))
  launch,capture=clocks[0][1],clocks[1][1];arrival=val('data arrival time');required=val('data required time');slack=val('slack ')
  row=dict(launch_clock_ns=launch,capture_clock_ns=capture,data_delay_ns=arrival-launch,clock_skew_ns=capture-launch,effective_hold_requirement_ns=required-capture,slack_ns=slack)
  assert abs(slack-rows[key]['slack_ns'])<1e-6 and abs(row['data_delay_ns']-row['clock_skew_ns']-row['effective_hold_requirement_ns']-slack)<2e-7
  out[key]=row
 assert set(out)==set(rows);return r,out,sha(d/'selected-min.rpt')
a,old,oldsha=read(439);b,new,newsha=read(440)
assert a['diagnosis_receipt_sha256']==b['diagnosis_receipt_sha256']and a['failing_paths_sha256']==b['failing_paths_sha256']and set(old)==set(new)
rows=[]
for key in sorted(old):
 x,y=old[key],new[key];effects=dict(data_delay_ps=1000*(y['data_delay_ns']-x['data_delay_ns']),clock_skew_ps=-1000*(y['clock_skew_ns']-x['clock_skew_ns']),effective_hold_requirement_ps=-1000*(y['effective_hold_requirement_ns']-x['effective_hold_requirement_ns']))
 delta=1000*(y['slack_ns']-x['slack_ns']);assert abs(sum(effects.values())-delta)<.0003
 rows.append(dict(startpoint=key[0],endpoint=key[1],old=x,new=y,slack_delta_ps=delta,effects_on_slack_ps=effects))
result=dict(qualified=False,all_source_pairs_old_positive_new_negative=all(x['old']['slack_ns']>=0 and x['new']['slack_ns']<0 for x in rows),source_reports_sha256=dict(old=oldsha,new=newsha),old_inputs=a['inputs'],new_inputs=b['inputs'],producer_sha256=sha(Path(__file__)),rows=rows,scope='Actual same24 constrained min paths. Slack=data-delay minus capture/launch skew minus effective hold requirement. Clock/data effects measured separately; no qualification or fixed-clock claim.')
(B/'COMPARISON.json').write_text(json.dumps(result,indent=2)+'\n')
print('pairs',len(rows),'all old positive/new negative',result['all_source_pairs_old_positive_new_negative'])
for row in sorted(rows,key=lambda x:x['new']['slack_ns'])[:5]:print(row['endpoint'],'old_ps',1000*row['old']['slack_ns'],'new_ps',1000*row['new']['slack_ns'],'effects',row['effects_on_slack_ps'])
