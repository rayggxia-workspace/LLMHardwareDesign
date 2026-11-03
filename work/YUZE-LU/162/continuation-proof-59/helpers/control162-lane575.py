from pathlib import Path
import json,hashlib,time,collections
import numpy as np,scipy
from scipy.optimize import linear_sum_assignment
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;o=h/'LLMHardwareDesign-deliveries/issue-162/lane-assignment-diagnostic-575';assert not o.exists();o.mkdir();gp=h/'LLMHardwareDesign-deliveries/issue-162/local-cut-inputs-560/boundary-graph.json';inp=r/'work/YUZE-LU/162/continuation-proof-58/r256-composition-453/upper-candidates/5400/route/router-input.txt';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(gp)=='49ba0e348f3583f6facdf60e771fe6f1329b46fe5aac872c3828d4b61ddb1a68';g=json.loads(gp.read_text());terms={}
for line in inp.read_text().splitlines()[1:]:
 a=line.split();terms[a[0]]=[tuple(map(int,a[2+2*j:4+2*j]))for j in range(int(a[1]))]
hp=lambda ps:max(x for x,y in ps)-min(x for x,y in ps)+max(y for x,y in ps)-min(y for x,y in ps)
after={k:list(v)for k,v in terms.items()};rows=[];total_old=total_new=0;old_output=new_output=0
for row in g['boundary_links']['links']:
 name=row['instance'];lanes=row['lanes'];targets=[];outputs=[];source=[];indexes=[];keys=[]
 for lane in lanes:
  key='net_'+str(lane['input_bit']);c=g['connections'][str(lane['input_bit'])];es=[c['driver'],*c['sinks']];i=next(i for i,e in enumerate(es)if e['instance']==name and e['pin']=='in_data['+str(lane['lane'])+']');keys.append(key);indexes.append(i);targets.append(terms[key][i]);source.append(terms[key][0]);outputs.append(terms['net_'+str(lane['output_bit'])][0])
 n=len(lanes);cost=np.full((n,n),10**15,dtype=np.int64);old_pairs=[abs(a[0]-b[0])+abs(a[1]-b[1])for a,b in zip(source,targets)]
 for i,lane in enumerate(lanes):
  old=terms[keys[i]];xs,ys=zip(*old);ok='net_'+str(lane['output_bit']);out_old=terms[ok];baseline=hp(out_old)
  for j in range(n):
   x,y=targets[j];pair=abs(source[i][0]-x)+abs(source[i][1]-y);new_out=hp([outputs[j],*out_old[1:]])
   if min(xs)<=x<=max(xs)and min(ys)<=y<=max(ys)and pair<=old_pairs[i]and new_out<=baseline:cost[i,j]=pair*1000000+new_out
 ii,jj=linear_sum_assignment(cost);assert list(ii)==list(range(n))and all(cost[i,j]<10**15 for i,j in zip(ii,jj));mapping=list(map(int,jj));new_pairs=[]
 for i,j in enumerate(mapping):
  after[keys[i]][indexes[i]]=targets[j];ok='net_'+str(lanes[i]['output_bit']);after[ok][0]=outputs[j];new_pairs.append(abs(source[i][0]-targets[j][0])+abs(source[i][1]-targets[j][1]));old_output+=hp(terms[ok]);new_output+=hp(after[ok])
 total_old+=sum(old_pairs);total_new+=sum(new_pairs)
 if mapping!=list(range(n)):rows.append(dict(instance=name,old_lanes=[x['lane']for x in lanes],new_lane_for_original_lane=[lanes[j]['lane']for j in mapping],source_pair_sum_old_um=4*sum(old_pairs),source_pair_sum_new_um=4*sum(new_pairs)))
assert all(hp(after[k])<=hp(v)for k,v in terms.items());bits={x['input_bit']for row in g['boundary_links']['links']for x in row['lanes']};old_native=sum(hp(terms['net_'+str(b)])for b in bits);new_native=sum(hp(after['net_'+str(b)])for b in bits)
result=dict(passed=True,whole_system_qualified=False,actual_input=str(inp),actual_input_sha256=sha(inp),actual_graph_sha256=sha(gp),script_sha256=sha(__file__),scipy=scipy.__version__,numpy=np.__version__,link_instances=316,valid_lanes=2261,unique_native_input_nets=len(bits),changed_lane_assignment_groups=len(rows),old_pair_sum_um=4*total_old,new_pair_sum_um=4*total_new,old_native_net_hpwl_sum_um=4*old_native,new_native_net_hpwl_sum_um=4*new_native,old_output_hpwl_sum_um=4*old_output,new_output_hpwl_sum_um=4*new_output,all_actual_net_hpwl_nonincreasing=True,proposals=rows,scope='Local read-only assignment diagnosis on actual S5380 geometry. Permute only existing live lanes within each fixed Link8, retaining each input/output pairing; spare padding lanes not used. Forbid any native source-to-input pair growth, any new input endpoint outside its original entire native-net bbox, or any output-net HPWL growth; independently recompute all actual net HPWL after simultaneous proposed permutations, including repeated native fanout. No RTL/graph/pin/macro/remote-job mutation and no qualification. Even a shorter HPWL does not guarantee actual routed tree length, native pin capacitance/slew, logical/function timing equivalence or any final physical gate; implementing proposals would require fresh full evidence.',time=time.time());(o/'receipt.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:result[k]for k in ['passed','changed_lane_assignment_groups','old_pair_sum_um','new_pair_sum_um','old_native_net_hpwl_sum_um','new_native_net_hpwl_sum_um','old_output_hpwl_sum_um','new_output_hpwl_sum_um']}))
