import subprocess,shlex
q="""from pathlib import Path
import json,hashlib,time,copy,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');old=b/'r256-composition-359/topology';new=b/'r256-composition-453/topology';out=b/'r256-padding-whole-topology-audit-457';assert not out.exists();paths=[old/'topology.json',new/'topology.json',old/'boundary-graph.json',new/'boundary-graph.json'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def structural(x):
 if isinstance(x,list):return [structural(v)for v in x]
 if not isinstance(x,dict):return x
 return {k:({kk:structural(vv)for kk,vv in v.items()if kk!='src'}if k=='attributes'and isinstance(v,dict)else structural(v))for k,v in x.items()}
a,c=[structural(json.loads(p.read_text())['modules']['control_system'])for p in paths[:2]];ag,cg=[json.loads(p.read_text())for p in paths[2:]];assert ag['instances']==cg['instances'];assert set(a)==set(c);restored=copy.deepcopy(c);changes=[];consumers=collections.Counter()
for cell in c['cells'].values():
 for port,bits in cell['connections'].items():
  if cell['port_directions'][port]=='input':consumers.update(bits)
for port in c['ports'].values():
 if port['direction']=='output':consumers.update(port['bits'])
for row in cg['boundary_links']['links']:
 name=row['instance'];before=a['cells'][name]['connections'];after=c['cells'][name]['connections'];n=len(row['lanes']);expected=list(before['in_data']);expected[n:]=after['reset']*(8-n);assert expected==after['in_data'];assert all(consumers[bit]==0 for bit in after['out_data'][n:]);restored['cells'][name]['connections']['in_data']=before['in_data']
 for i,(x,y)in enumerate(zip(before['in_data'],after['in_data'])):
  if x!=y:changes.append(dict(instance=name,lane=i,old_payload_net=x,new_existing_reset_net=y))
assert restored==a,'A field other than unconsumed padding inputs changed'
assert len(changes)==267
# Check all retained original receivers directly, rather than accepting the
# generator contraction Boolean. Normal tokens distinguish every source bit.
av={bit:bit*1000003 for cell in a['cells'].values()for bits in cell['connections'].values()for bit in bits};cv=av.copy()
for row in cg['boundary_links']['links']:
 for mod,values in [(a,av),(c,cv)]:
  co=mod['cells'][row['instance']]['connections']
  for source,target in zip(co['in_data'],co['out_data']):values[target]=values[source]
checks=0
for name,cell in a['cells'].items():
 if cell['type']=='control_link8':continue
 for port,bits in cell['connections'].items():
  if cell['port_directions'][port]=='input':
   assert [av[x]for x in bits]==[cv[x]for x in c['cells'][name]['connections'][port]];checks+=len(bits)
for name,port in a['ports'].items():
 if port['direction']=='output':assert [av[x]for x in port['bits']]==[cv[x]for x in c['ports'][name]['bits']];checks+=len(port['bits'])
out.mkdir();receipt=dict(passed=True,captured_at=time.time(),inputs={str(p):sha(p)for p in paths},actual_changed_pins=len(changes),all_other_module_fields_exact_ignoring_only_src=True,unchanged_instances=len(ag['instances']),independent_live_consuming_pin_checks=checks,changes=changes,whole_system_qualified=False,scope='Actual whole current359/453 topology structural delta and independent distinct data tokens. All267 edits are unused input lanes whose outputs have no module/host consumers; all other structural fields including types, parameters, attributes except src, clocks, resets, active connections, output IDs and ports exact. This metadata audit does not replace real final-cell programs, transient/reset simulation, timing, geometry or joint qualification.');(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(dict(passed=True,changes=len(changes),live_consuming_pin_checks=checks)))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
