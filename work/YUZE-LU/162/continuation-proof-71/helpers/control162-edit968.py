from pathlib import Path
p=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1')
def edit(name,changes):
 f=p/name;s=f.read_text(encoding='utf-8')
 for a,z in changes:
  assert s.count(a)==1,(name,a);s=s.replace(a,z,1)
 f.write_bytes(s.encode())
edit('tree_router.cpp',[
 ('#include "pin_access_reservation.h"','#include "pin_access_reservation.h"\n#include "native_prefix_seed.h"'),
 ('argc>18','argc>20'),
 ('bool release_pin_reservations=false,','string native_seed_input;bool native_flexible=false,release_pin_reservations=false,'),
 ('  if(option=="--release-pin-reservations")','  if(option=="--native-prefix-flexible"){if(native_flexible)throw runtime_error("duplicate flexible native prefix option");native_flexible=true;}\n  else if(option.rfind("--native-prefix-input=",0)==0){if(!native_seed_input.empty())throw runtime_error("duplicate native prefix input");native_seed_input=option.substr(22);if(native_seed_input.empty())throw runtime_error("empty native prefix input");}\n  else if(option=="--release-pin-reservations")'),
 (' if(release_pin_reservations&&', ' if(native_flexible&&(!native_prefix_first||pin_policy!="none"))throw runtime_error("flexible native prefix requires native-first and no proxy reservations");\n if(!native_seed_input.empty()&&!native_flexible)throw runtime_error("native seed requires flexible native prefix");\n if(release_pin_reservations&&'),
 (' // Optional initial routing schedule,', ''' if(!native_seed_input.empty()){
  uint64_t vertices=import_native_prefix(native_seed_input,nx,ny,locked_count,names,ends,fixed,wire_limits,branches,trees,usage);
  cout<<"{\\"native_seed_prefix_loaded\\":true,\\"nets\\":"<<locked_count<<",\\"vertices\\":"<<vertices<<"}"<<endl;
 }
 // Optional initial routing schedule,'''),
 ('(!native_stage&&n<locked_count)))','(!native_stage&&n<locked_count&&!native_flexible)))'),
 ('   bool tracing=phase_trace', '''   if((native_stage&&!native_seed_input.empty()&&!iteration)||(!native_stage&&native_flexible&&!iteration&&n<locked_count)){++number;continue;}
   bool tracing=phase_trace'''),
 ('throw runtime_error("native freeze ownership conflict");fixed[v]=n;','throw runtime_error("native freeze ownership conflict");if(!native_flexible)fixed[v]=n;'),
 ('   cout<<"{\\"native_prefix_stage_passed\\":true,\\"native_rounds\\":"<<iteration+1<<",\\"frozen_nets\\":"<<locked_count<<"}"<<endl;', '''   if(native_flexible)cout<<"{\\"native_prefix_stage_passed\\":true,\\"native_rounds\\":"<<iteration+1<<",\\"frozen_nets\\":0,\\"warm_started_nets\\":"<<locked_count<<"}"<<endl;
   else cout<<"{\\"native_prefix_stage_passed\\":true,\\"native_rounds\\":"<<iteration+1<<",\\"frozen_nets\\":"<<locked_count<<"}"<<endl;'''),
])
edit('tree_router_cpp.py',[
 ('release_pin_reservations=False):','release_pin_reservations=False,native_prefix_flexible=False,native_prefix_input=None):'),
 ('    assert len(set(locked_names))', "    assert not native_prefix_flexible or(native_prefix_first and pin_access_policy=='none')\n    assert native_prefix_input is None or native_prefix_flexible\n    if native_prefix_flexible:extra_cli.append('--native-prefix-flexible')\n    assert len(set(locked_names))"),
 ('    trial_proof=None;selected_seed=seed', '''    seed_proof=None
    if native_prefix_input is not None:
        config=Path(native_prefix_input);cfg=json.loads(config.read_text())
        assert set(cfg)=={'prefix','prefix_sha256','input','input_sha256'}
        prefix_source=Path(cfg['prefix']);prior_input=Path(cfg['input'])
        assert hashlib.sha256(prefix_source.read_bytes()).hexdigest()==cfg['prefix_sha256']
        assert hashlib.sha256(prior_input.read_bytes()).hexdigest()==cfg['input_sha256']
        ah,ab=prior_input.read_bytes().split(b'\\n',1);zh,zb=inp.read_bytes().split(b'\\n',1)
        a=list(map(int,ah.split()));z=list(map(int,zh.split()))
        assert ab==zb and all(a[i]==z[i]for i in (0,1,2,6,7,9)), 'Seed geometry/terminals/wire envelope mismatch'
        from router_conflict_snapshot import inspect
        seed_check=inspect(prefix_source,{n:terminals[n]for n in locked_names},nx,ny,wire_limits)
        assert seed_check['conflict_nodes']==0 and seed_check['all_trees_flood_verified']and seed_check['all_wire_budgets_verified']
        seed_proof=dict(config=str(config),config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),prefix=str(prefix_source),prefix_sha256=cfg['prefix_sha256'],input=str(prior_input),input_sha256=cfg['input_sha256'],body_byte_exact=True,independent=seed_check)
        extra_cli.append('--native-prefix-input='+str(prefix_source))
    trial_proof=None;selected_seed=seed'''),
 ("assert len(stages)==1 and stages[0]['native_prefix_stage_passed']and stages[0]['frozen_nets']==len(locked_names)", "assert len(stages)==1 and stages[0]['native_prefix_stage_passed']\n        assert (stages[0]['frozen_nets']==0 and stages[0]['warm_started_nets']==len(locked_names))if native_prefix_flexible else stages[0]['frozen_nets']==len(locked_names)\n        prefix_changed=0"),
 ("                assert paths==branches[name],('Frozen prefix differs from final full route',name)", "                prefix_changed+=paths!=branches[name]\n                if not native_prefix_flexible:assert paths==branches[name],('Frozen prefix differs from final full route',name)"),
 ("        native_proof=dict(stage=stages[0]", "        native_proof=dict(stage=stages[0]"),
 ('frozen_prefix_matches_full_route=True,','frozen_prefix_matches_full_route=(not native_prefix_flexible),'),
 ('    for name,limit in wire_limits.items():', '''        if native_prefix_flexible:
            from router_conflict_snapshot import inspect
            initial=inspect(prefix,{n:terminals[n]for n in locked_names},nx,ny,wire_limits)
            assert initial['conflict_nodes']==0 and initial['all_trees_flood_verified']and initial['all_wire_budgets_verified']
            native_proof.update(prefix_is_frozen=False,prefix_kind='M11/M12 search warm start; M1-M10 unchanged',initial_independent=initial,final_native_paths_changed=prefix_changed,seed=seed_proof)
            if seed_proof:assert sha(prefix)==seed_proof['prefix_sha256']
    for name,limit in wire_limits.items():'''),
 ('        release_pin_reservations=release_pin_reservations,','        native_prefix_flexible=native_prefix_flexible,native_prefix_seed=seed_proof,release_pin_reservations=release_pin_reservations,'),
])
edit('system_upper.py',[
 ("    p.add_argument('--route-release-pin-reservations',action='store_true')", "    p.add_argument('--route-release-pin-reservations',action='store_true')\n    p.add_argument('--route-native-prefix-flexible',action='store_true')\n    p.add_argument('--route-native-prefix-input',type=Path)"),
 ('    assert not a.route_release_pin_reservations', "    assert not a.route_native_prefix_flexible or(a.route_native_prefix_first and a.route_pin_access=='none')\n    assert not a.route_native_prefix_input or a.route_native_prefix_flexible\n    assert not a.route_release_pin_reservations"),
 ('            else:\n                branches,proof=route_compiled(', '''            else:
                if a.route_native_prefix_input:
                    cfg=json.loads(a.route_native_prefix_input.read_text())
                    for path in [a.route_native_prefix_input,Path(cfg['prefix']),Path(cfg['input'])]:receipt['inputs'][str(path)]=sha(path)
                branches,proof=route_compiled('''),
 ('release_pin_reservations=a.route_release_pin_reservations)', 'release_pin_reservations=a.route_release_pin_reservations,native_prefix_flexible=a.route_native_prefix_flexible,native_prefix_input=a.route_native_prefix_input)'),
])
print('flexible M11/M12 prefix warm start + validated seed; fixed macro interior and final gates unchanged')
