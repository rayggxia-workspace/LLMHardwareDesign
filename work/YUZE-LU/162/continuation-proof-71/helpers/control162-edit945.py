from pathlib import Path
p=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1')
def edit(name,changes):
 f=p/name;s=f.read_text(encoding='utf-8')
 for a,z in changes:
  assert s.count(a)==1,(name,a);s=s.replace(a,z,1)
 f.write_bytes(s.encode())
edit('tree_router.cpp',[
 ('argc>17','argc>18'),
 ('bool native_batch=false,native_prefix_first=false;', 'bool release_pin_reservations=false,native_batch=false,native_prefix_first=false;'),
 ('  if(option=="--native-refresh=8"', '  if(option=="--release-pin-reservations"){if(release_pin_reservations)throw runtime_error("duplicate pin reservation release option");release_pin_reservations=true;}\n  else if(option=="--native-refresh=8"'),
 (' if(native_refresh&&(!native_prefix_first||!native_batch))', ' if(release_pin_reservations&&(!native_prefix_first||pin_policy!="ordinary-first"))throw runtime_error("pin reservation release requires ordinary-first native-prefix mode");\n if(native_refresh&&(!native_prefix_first||!native_batch))'),
 ('   for(int n=locked_count;n<count;++n)for(int v:ends[n]){auto c=coord(v);bool legal=false;', '''   if(release_pin_reservations){
    // These are search reservations, not fabricated wires. Once the real
    // native paths are frozen, retain those paths and every original M11
    // landing, and let ordinary nets negotiate actual wire occupancy.
    uint64_t cleared=0,landings=0;
    for(int v=0;v<size;++v)if(fixed[v]>=locked_count){fixed[v]=-1;++cleared;}
    for(int n=locked_count;n<count;++n)for(int v:ends[n]){
     if(fixed[v]>=0&&fixed[v]!=n)throw runtime_error("landing lost during reservation release");
     fixed[v]=n;++landings;
    }
    for(int n=0;n<locked_count;++n)for(int v:trees[n])
     if(fixed[v]!=n||usage[v]!=1)throw runtime_error("native freeze changed during reservation release");
    if(cleared<landings)throw runtime_error("invalid released reservation count");
    cout<<"{\\"unwired_search_reservations_released\\":"<<cleared-landings<<",\\"actual_m11_landings_restored\\":"<<landings<<",\\"frozen_native_paths_unchanged\\":true}"<<endl;
   }
   for(int n=locked_count;n<count;++n)for(int v:ends[n]){auto c=coord(v);bool legal=false;'''),
])
edit('tree_router_cpp.py',[
 ('native_refresh_period=0):','native_refresh_period=0,release_pin_reservations=False):'),
 ('    assert len(set(locked_names))', "    assert not release_pin_reservations or(native_prefix_first and pin_access_policy=='ordinary-first')\n    if release_pin_reservations:extra_cli.append('--release-pin-reservations')\n    assert len(set(locked_names))"),
 ('rounds=native_rounds,refresh_trace=', "rounds=native_rounds,pin_release_trace=[r for r in trace if 'unwired_search_reservations_released'in r],refresh_trace="),
 ('        native_refresh_period=native_refresh_period,', '        release_pin_reservations=release_pin_reservations,native_refresh_period=native_refresh_period,'),
])
edit('system_upper.py',[
 ("    p.add_argument('--route-native-refresh',type=int,choices=[0,8,16],default=0)", "    p.add_argument('--route-native-refresh',type=int,choices=[0,8,16],default=0)\n    p.add_argument('--route-release-pin-reservations',action='store_true')\n    p.add_argument('--pin-release-regression-config',type=Path)"),
 ('    assert not a.route_native_refresh', "    assert not a.route_release_pin_reservations or(a.route_native_prefix_first and a.route_pin_access=='ordinary-first')\n    assert not a.route_native_refresh"),
 ('native_refresh_period=a.route_native_refresh)', 'native_refresh_period=a.route_native_refresh,release_pin_reservations=a.route_release_pin_reservations)'),
])
print('opt-in phase-boundary cleanup; all physical landings and frozen wires retained')
