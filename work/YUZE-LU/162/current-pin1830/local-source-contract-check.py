from pathlib import Path
import json,sys,hashlib,copy,collections
b=Path(__file__).parent;root=b/'control162-math-data1790';t=b/'control162-topology-data1825';repo=b/'LLMHardwareDesign-worktrees/issue-162-control';out=b/'control162-groupcheck1831';assert not out.exists();out.mkdir();sys.path.insert(0,str(repo/'project/experiments/control_v1'));from boundary_links import insert;from current_pin_groups import reference_counts
for folder in [root,t]:
 for name,r in json.loads((folder/'reception.json').read_bytes()).items():data=(folder/name).read_bytes();assert len(data)==r['bytes']and hashlib.sha256(data).hexdigest()==r['sha256']
g=json.loads((root/'boundary-graph.json').read_bytes());p=json.loads((root/'placement.json').read_bytes());m=json.loads((root/'physical.json').read_bytes());old=json.loads((t/'old-physical.json').read_bytes());original=json.loads((t/'original-topology.json').read_bytes())['modules']['control_system'];expected=json.loads((t/'topology.json').read_bytes())['modules']['control_system'];pins=collections.defaultdict(dict)
for bit,c in g['connections'].items():
 for end,xy in zip([c['driver'],*c['sinks']],p['terminals']['net_'+bit]):
  name=end['instance']
  if name=='TOP':continue
  top=g['instances'][name];point=[xy[axis]*4+[.095,.070][axis]-p['placements_um'][name][axis]for axis in range(2)];row=pins[top].get(end['pin'])
  if row:assert max(abs(row['xy_um'][axis]-point[axis])for axis in range(2))<1e-6
  pins[top][end['pin']]=dict(pin=end['pin'],xy_um=point)
reference=copy.deepcopy(pins);reference['control_s_arbiter_r7']={r['pin']:r for r in json.loads((t/'old-s-port-pins.json').read_bytes())['pins']};sources=list(dict.fromkeys(r['source_instance']for r in g['boundary_links']['links']if r['source_instance'].startswith('macro_')));fanout=['s_port:dout','controller:task_data','controller:task_last'];legacy=copy.deepcopy(original);lp=insert(legacy,old,reference,sources,fanout,local_reset_padding=True);assert legacy==expected,'Default producer changed exact previous topology';prior=copy.deepcopy(g['boundary_links']);prior.pop('grouping_reference');assert lp==prior,'Default grouping proof changed';assert json.dumps(lp,indent=2)==json.dumps(prior,indent=2);legacy_document=json.loads((t/'original-topology.json').read_bytes());legacy_document['modules']['control_system']=legacy;assert (json.dumps(legacy_document,indent=2)+'\n').encode()==(t/'topology.json').read_bytes(),'Default full topology rawbytes changed'
new=copy.deepcopy(original);counts=reference_counts(lp['links']);proof=insert(new,m,pins,sources,fanout,local_reset_padding=True,reference_group_counts=counts);assert set(new['cells'])==set(expected['cells']);assert len(proof['links'])==316 and len(proof['reset_banks']['banks'])==25;assert collections.Counter((r['source_instance'],r['fanout_branch'])for r in proof['links'])==counts
def worst(proof,plan):
 values=[]
 for r in proof['links']:
  if r['source_instance']!='s_port':continue
  points=[plan['control_s_arbiter_r7'][lane['source_pin']]['xy_um']for lane in r['lanes']];values.append(sum(max(p[axis]for p in points)-min(p[axis]for p in points)for axis in range(2)))
 return max(values)
maxspan_old=worst(lp,pins);maxspan_new=worst(proof,pins);assert maxspan_new<100 and maxspan_old>2500
# Exact payload contraction is checked independently by insert for both variants.
for name,cell in new['cells'].items():assert cell['type']==expected['cells'][name]['type']
for r in proof['links']:
 assert len(r['lanes'])+r['padded_input_lanes']==8 and r['payload_register_bits']==0 and r['state_bits']==1
assert new['ports']==expected['ports']and new.get('parameter_default_values')==expected.get('parameter_default_values')
(out/'pins-derived-actual.json').write_text(json.dumps(pins));(out/'module-current-groups.json').write_text(json.dumps(new));(out/'links-current-groups.json').write_text(json.dumps(proof));receipt=dict(passed=True,whole_system_qualified=False,default_topology_raw_bytes_exact=True,default_complete_linkproof_serialization_exact=True,physical_instances=len(new['cells']),links=316,reset_banks=25,all_physical_types_and_inventory_unchanged=True,payload_contraction_exact=True,reference_group_counts_exact=True,old_s_port_group_maximum_current_pin_span_um=maxspan_old,new_s_port_group_maximum_current_pin_span_um=maxspan_new,scope='Pure local source-contract diagnostic on exact fetched actual1773/reference359 inputs. New group lanes follow actual3200native pins; old1470 coordinates only determine unchanged inventory counts. Same316fixedLink8/25banks, spatially ordered equivalentreset outputs. All23native macros unchanged; actualnewYosys/3initialfunction/nativeRC/P&R/3RC300MHz andtracequalification stillrequired.',source_sha256={name:hashlib.sha256((repo/'project/experiments/control_v1'/name).read_bytes()).hexdigest()for name in ['current_pin_groups.py','boundary_links.py','reset_link_banks.py','topology.py']})
from current_pin_groups import balance,spatial_reset_order
rejections=[]
def reject(name,call):
 try:call()
 except (AssertionError,KeyError):rejections.append(name)
 else:raise AssertionError('Malformed profile accepted: '+name)
chunks=[(0,'dest',[(0,'p0',1,[]),(4,'p1',2,[])])]
reject('too_few_reference_groups',lambda:balance('s',chunks,{('s','dest'):0}))
reject('more_groups_than_lanes',lambda:balance('s',chunks,{('s','dest'):3}))
reject('missing_destination',lambda:balance('s',chunks,{}))
reject('extra_destination',lambda:balance('s',chunks,{('s','dest'):1,('s','other'):1}))
reject('missing_reference_link',lambda:reference_counts(lp['links'][:-1]))
bad=copy.deepcopy(lp['links']);next(r for r in bad if r['source_instance']=='s_port')['fanout_branch']='invalid';reject('changed_reference_target',lambda:reference_counts(bad))
sr=[r for r in proof['links']if r['source_instance']=='s_port'];reject('missing_spatial_load',lambda:spatial_reset_order(sr[:-1]))
bad=copy.deepcopy(sr);bad[0]['source_pin_die_um']=[1470,1470];reject('wrong_native_die',lambda:spatial_reset_order(bad))
bad=copy.deepcopy(sr);bad[0]['source_instance']='macro_s';reject('wrong_spatial_owner',lambda:spatial_reset_order(bad))
receipt['malformed_profiles_rejected']=rejections;assert len(rejections)==9
(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
