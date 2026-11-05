from pathlib import Path
p=Path('project/experiments/control_v1');f=p/'tree_router.cpp';s=f.read_text(encoding='utf-8')
def sub(a,z):
 global s
 assert s.count(a)==1,a;s=s.replace(a,z,1)
sub('if(argc<3||argc>14)','if(argc<3||argc>15)')
sub(' bool native_prefix_first=false;', ' int native_maze_budget=0;bool native_prefix_first=false;')
sub('  if(option=="--native-prefix-first")', '  if(option=="--native-zero-maze=16384"||option=="--native-zero-maze=65536"){if(native_maze_budget)throw runtime_error("duplicate native zero-maze option");native_maze_budget=stoi(option.substr(option.find(\'=\')+1));}\n  else if(option=="--native-prefix-first")')
sub(' if(pin_policy_option&&!native_prefix_first)', ' if(native_maze_budget&&!native_prefix_first)throw runtime_error("native zero-maze requires staged native-prefix mode");\n if(pin_policy_option&&!native_prefix_first)')
sub('  uint64_t zero_maze_attempts=0,zero_maze_hits=0,zero_maze_expanded=0;', '  uint64_t zero_maze_attempts=0,zero_maze_hits=0,zero_maze_expanded=0;\n  uint64_t native_maze_attempts=0,native_maze_hits=0,native_maze_rejected=0,native_maze_expanded=0;')
a='    if(path.empty()){\n    if(pareto_wire_budget&&n<locked_count&&wire_limits[n]>=0){'
sub(a,r'''    // Bounded strict-zero candidate before the unchanged native finite
    // search. Reject any candidate beyond the actual remaining wire budget.
    // Empty/capped/over-budget paths always yield to the original solver.
    if(path.empty()&&native_stage&&native_maze_budget&&n<locked_count&&wire_limits[n]>=0){
     ++native_maze_attempts;
     path=ordinary_zero_maze(nx,ny,start,[&](int v){return !usage[v]&&(fixed[v]<0||fixed[v]==n);},
       [&](int v){return marked[v]==epoch;},h,nonpreferred_cost,native_maze_budget,
       visited,distance,parent,search,native_maze_expanded);
     if(!path.empty()){
      int wires=0;for(size_t j=1;j<path.size();++j)wires+=path[j-1]/plane==path[j]/plane;
      if(wires<=wire_limits[n]-used_wire_edges)++native_maze_hits;
      else{++native_maze_rejected;path.clear();}
     }
    }
    if(path.empty()){
    if(pareto_wire_budget&&n<locked_count&&wire_limits[n]>=0){''')
a='  if(ordinary_maze_budget)cout<<';sub(a,'  if(native_stage&&native_maze_budget)cout<<"{\\\"round\\\":"<<iteration<<",\\\"native_zero_maze_budget\\\":"<<native_maze_budget<<",\\\"native_zero_maze_attempts\\\":"<<native_maze_attempts<<",\\\"native_zero_maze_hits\\\":"<<native_maze_hits<<",\\\"native_zero_maze_wire_rejected\\\":"<<native_maze_rejected<<",\\\"native_zero_maze_expanded\\\":"<<native_maze_expanded<<"}"<<endl;\n'+a)
# Python generator escapes inside this single C++ line need one slash.
s='\n'.join(l.replace('\\\\"','\\"')if 'native_zero_maze_budget\\'in l else l for l in s.splitlines())+'\n';f.write_bytes(s.encode())
f=p/'tree_router_cpp.py';s=f.read_text(encoding='utf-8');sub('pin_access_policy="none"):', 'pin_access_policy="none",native_zero_maze_budget=0):');sub('    assert len(set(locked_names))==len(locked_names)', "    assert native_zero_maze_budget in (0,16384,65536)and(not native_zero_maze_budget or native_prefix_first)\n    if native_zero_maze_budget:extra_cli.append('--native-zero-maze='+str(native_zero_maze_budget))\n    assert len(set(locked_names))==len(locked_names)")
sub('native_proof=dict(stage=stages[0],rounds=native_rounds,',"native_proof=dict(stage=stages[0],rounds=native_rounds,zero_maze_trace=[r for r in native_rows if 'native_zero_maze_attempts'in r],")
sub('        native_prefix_first=native_prefix_first,','        native_zero_maze_budget=native_zero_maze_budget,\n        native_prefix_first=native_prefix_first,');f.write_bytes(s.encode())
f=p/'system_upper.py';s=f.read_text(encoding='utf-8');a="    p.add_argument('--route-native-prefix-first',action='store_true')";sub(a,a+"\n    p.add_argument('--route-native-zero-maze',type=int,choices=[0,16384,65536],default=0)")
sub("    assert a.route_pin_access=='none' or a.route_native_prefix_first", "    assert not a.route_native_zero_maze or a.route_native_prefix_first\n    assert a.route_pin_access=='none' or a.route_native_prefix_first")
sub('pin_access_policy=a.route_pin_access)', 'pin_access_policy=a.route_pin_access,native_zero_maze_budget=a.route_native_zero_maze)');f.write_bytes(s.encode())
