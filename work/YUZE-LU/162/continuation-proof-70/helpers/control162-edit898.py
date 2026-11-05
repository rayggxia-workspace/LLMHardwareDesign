from pathlib import Path
p=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1')
def edit(name,replacements):
 f=p/name;s=f.read_text(encoding='utf-8')
 for a,z in replacements:
  assert s.count(a)==1,(name,a,s.count(a));s=s.replace(a,z,1)
 f.write_bytes(s.encode())
edit('tree_router.cpp',[
 ('argc>15','argc>16'),
 ('bool native_prefix_first=false;','bool native_batch=false,native_prefix_first=false;'),
 ('  if(option=="--native-zero-maze=16384"','  if(option=="--native-batch-ripup"){if(native_batch)throw runtime_error("duplicate native batch option");native_batch=true;}\n  else if(option=="--native-zero-maze=16384"'),
 ('option=="--pin-access=none")','option=="--pin-access=none"||option=="--pin-access=ordinary-first")'),
 (' if(native_maze_budget&&!native_prefix_first)', ' if(native_batch&&!native_prefix_first)throw runtime_error("native batch requires staged native-prefix mode");\n if(native_maze_budget&&!native_prefix_first)'),
 (' if(native_prefix_first&&pin_policy=="all"){', ' if(native_prefix_first&&pin_policy=="ordinary-first"){auto r=reserve_pin_access(nx,ny,locked_count,ends,fixed,usage,seed,string(argv[2])+".pin-access.json",true);cout<<"{\\\"pin_access_policy\\\":\\\"ordinary-first\\\",\\\"assigned\\\":"<<r.assigned<<",\\\"terminals\\\":"<<r.terminals<<"}"<<endl;}\n if(native_prefix_first&&pin_policy=="all"){'),
 ('  int number=0;', '''  // Snapshot all dirty native trees BEFORE changing occupancy. Remove them
  // together, so another dirty old path cannot trap the first rerouted net.
  // A newly empty tree must never satisfy the clean-tree skip below.
  vector<unsigned char>batch_removed(count,0);int removed=0;
  if(native_stage&&native_batch&&iteration){
   for(int n=0;n<locked_count;++n){
    if(trees[n].empty())throw runtime_error("missing native tree before batch");
    if(any_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]>1;})){batch_removed[n]=1;++removed;}
   }
   for(int n=0;n<locked_count;++n)if(batch_removed[n]){
    for(int v:trees[n]){if(!usage[v])throw runtime_error("batch usage underflow");--usage[v];}
    trees[n].clear();branches[n].clear();
   }
   cout<<"{\\"round\\":"<<iteration<<",\\"native_batch_removed_trees\\":"<<removed<<"}"<<endl;
  }
  int number=0;'''),
 ('if(tracing&&iteration&&negotiated_priority&&all_of(', 'if(tracing&&iteration&&negotiated_priority&&!batch_removed[n]&&all_of('),
 ('if(iteration&&negotiated_priority&&all_of(', 'if(iteration&&negotiated_priority&&!batch_removed[n]&&all_of('),
])
# Correct the generator's C++ string literal escaping, preserving other lines.
f=p/'tree_router.cpp';s=f.read_text();s='\n'.join(l.replace('\\\\"','\\"')if 'pin_access_policy\\'in l else l for l in s.splitlines())+'\n';f.write_bytes(s.encode())
edit('tree_router_cpp.py',[
 ('native_zero_maze_budget=0):','native_zero_maze_budget=0,native_batch_ripup=False):'),
 ("('none','all','after-native')","('none','all','after-native','ordinary-first')"),
 ('    assert len(set(locked_names))', "    assert not native_batch_ripup or native_prefix_first\n    if native_batch_ripup:extra_cli.append('--native-batch-ripup')\n    assert len(set(locked_names))"),
 ('rounds=native_rounds,zero_maze_trace=',"rounds=native_rounds,batch_trace=[r for r in native_rows if 'native_batch_removed_trees'in r],zero_maze_trace="),
 ('        native_zero_maze_budget=native_zero_maze_budget,','        native_batch_ripup=native_batch_ripup,native_zero_maze_budget=native_zero_maze_budget,'),
])
edit('system_upper.py',[
 ("choices=['none','all','after-native']","choices=['none','all','after-native','ordinary-first']"),
 ("    p.add_argument('--route-native-prefix-first',action='store_true')", "    p.add_argument('--route-native-prefix-first',action='store_true')\n    p.add_argument('--route-native-batch-ripup',action='store_true')"),
 ('    assert not a.route_native_zero_maze', '    assert not a.route_native_batch_ripup or a.route_native_prefix_first\n    assert not a.route_native_zero_maze'),
 ('native_zero_maze_budget=a.route_native_zero_maze)', 'native_zero_maze_budget=a.route_native_zero_maze,native_batch_ripup=a.route_native_batch_ripup)'),
])
print('edited 3 production sources; defaults unchanged')
