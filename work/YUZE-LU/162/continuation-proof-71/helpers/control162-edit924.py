from pathlib import Path
p=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1')
def edit(name,changes):
 f=p/name;s=f.read_text(encoding='utf-8')
 for a,z in changes:
  assert s.count(a)==1,(name,a);s=s.replace(a,z,1)
 f.write_bytes(s.encode())
edit('tree_router.cpp',[
 ('argc>16','argc>17'),
 ('int native_maze_budget=0;','int native_refresh=0,native_maze_budget=0;'),
 ('  if(option=="--native-batch-ripup")', '  if(option=="--native-refresh=8"||option=="--native-refresh=16"){if(native_refresh)throw runtime_error("duplicate native refresh option");native_refresh=stoi(option.substr(option.find(\'=\')+1));}\n  else if(option=="--native-batch-ripup")'),
 (' if(native_batch&&!native_prefix_first)', ' if(native_refresh&&(!native_prefix_first||!native_batch))throw runtime_error("native refresh requires staged native batch mode");\n if(native_batch&&!native_prefix_first)'),
 ('    if(any_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]>1;}))', '    if((native_refresh&&iteration%native_refresh==0)||any_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]>1;}))'),
 ('   cout<<"{\\"round\\":"<<iteration<<",\\"native_batch_removed_trees\\":"<<removed<<"}"<<endl;', '   if(native_refresh)cout<<"{\\"round\\":"<<iteration<<",\\"native_refresh_period\\":"<<native_refresh<<",\\"native_full_refresh\\":"<<(iteration%native_refresh==0?"true":"false")<<",\\"removed_trees\\":"<<removed<<"}"<<endl;\n   cout<<"{\\"round\\":"<<iteration<<",\\"native_batch_removed_trees\\":"<<removed<<"}"<<endl;'),
])
edit('tree_router_cpp.py',[
 ('native_batch_ripup=False):','native_batch_ripup=False,native_refresh_period=0):'),
 ('    assert len(set(locked_names))', "    assert native_refresh_period in (0,8,16)and(not native_refresh_period or(native_prefix_first and native_batch_ripup))\n    if native_refresh_period:extra_cli.append('--native-refresh='+str(native_refresh_period))\n    assert len(set(locked_names))"),
 ('rounds=native_rounds,batch_trace=', "rounds=native_rounds,refresh_trace=[r for r in native_rows if 'native_refresh_period'in r],batch_trace="),
 ('        native_batch_ripup=native_batch_ripup,','        native_refresh_period=native_refresh_period,native_batch_ripup=native_batch_ripup,'),
])
edit('system_upper.py',[
 ("    p.add_argument('--route-native-batch-ripup',action='store_true')", "    p.add_argument('--route-native-batch-ripup',action='store_true')\n    p.add_argument('--route-native-refresh',type=int,choices=[0,8,16],default=0)\n    p.add_argument('--native-refresh-regression-baseline',type=Path)"),
 ('    assert not a.route_native_batch_ripup', '    assert not a.route_native_refresh or(a.route_native_prefix_first and a.route_native_batch_ripup)\n    assert not a.route_native_batch_ripup'),
 ('native_batch_ripup=a.route_native_batch_ripup)', 'native_batch_ripup=a.route_native_batch_ripup,native_refresh_period=a.route_native_refresh)'),
])
print('refresh edit; original finite search and final physics unchanged')
