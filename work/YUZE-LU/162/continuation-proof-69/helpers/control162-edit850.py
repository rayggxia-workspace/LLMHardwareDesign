from pathlib import Path
p=Path('project/experiments/control_v1')
f=p/'tree_router_cpp.py';s=f.read_text(encoding='utf-8')
def sub(a,z):
 global s
 assert s.count(a)==1,a;s=s.replace(a,z,1)
sub('ordinary_zero_maze_budget=0):','ordinary_zero_maze_budget=0,native_prefix_first=False,pin_access_policy="none"):')
sub('    assert len(set(locked_names))==len(locked_names)', '''    assert pin_access_policy in ('none','all','after-native')
    assert not native_prefix_first or(critical_first and pareto_wire_budget)
    assert pin_access_policy=='none' or native_prefix_first
    if native_prefix_first:extra_cli+=['--native-prefix-first','--pin-access='+pin_access_policy]
    assert len(set(locked_names))==len(locked_names)''')
sub("        for before,after in [('input.txt',inp),('output.txt',result),('router.log',out/'router.log')]:shutil.copyfile(folder/before,after)","""        for before,after in [('input.txt',inp),('output.txt',result),('router.log',out/'router.log')]:shutil.copyfile(folder/before,after)
        if native_prefix_first:
            for suffix in ('.native-prefix.log','.native-prefix-paths.txt','.pin-access.json'):
                src=folder/('output.txt'+suffix)
                if suffix=='.pin-access.json' and pin_access_policy=='none':continue
                shutil.copyfile(src,Path(str(result)+suffix))""")
sub("    for name,limit in wire_limits.items():", """    native_proof=None
    if native_prefix_first:
        stages=[r for r in trace if 'native_prefix_stage_passed'in r]
        assert len(stages)==1 and stages[0]['native_prefix_stage_passed']and stages[0]['frozen_nets']==len(locked_names)
        prefix=Path(str(result)+'.native-prefix-paths.txt')
        with prefix.open()as f:
            assert int(f.readline())==len(locked_names)
            for name in locked_names:
                actual,count=f.readline().split();assert actual==name
                paths=[]
                for _ in range(int(count)):
                    values=list(map(int,f.readline().split()));assert len(values)==1+3*values[0]
                    paths.append([tuple(values[i:i+3])for i in range(1,len(values),3)])
                assert paths==branches[name],('Frozen prefix differs from final full route',name)
            assert not f.read().strip()
        native_log=Path(str(result)+'.native-prefix.log')
        native_rows=[json.loads(line)for line in native_log.read_text().splitlines()if line.startswith('{')]
        native_rounds=[r for r in native_rows if 'conflict_nodes'in r]
        assert native_rounds and native_rounds[-1]['conflict_nodes']==0
        assert len(native_rounds)==stages[0]['native_rounds']
        plan=Path(str(result)+'.pin-access.json')
        native_proof=dict(stage=stages[0],rounds=native_rounds,frozen_prefix_matches_full_route=True,
                          paths_sha256=sha(prefix),log_sha256=sha(native_log),
                          pin_plan_sha256=sha(plan)if plan.exists()else None)
    for name,limit in wire_limits.items():""")
sub('        nonpreferred_search_cost=nonpreferred_cost,', '        native_prefix_first=native_prefix_first,pin_access_policy=pin_access_policy,native_prefix_proof=native_proof,\n        pin_access_header_sha256=sha(source.with_name("pin_access_reservation.h")),\n        nonpreferred_search_cost=nonpreferred_cost,')
f.write_bytes(s.encode())
f=p/'system_upper.py';s=f.read_text(encoding='utf-8')
sub("    assert not a.route_ordinary_zero_maze or", "    assert a.route_pin_access=='none' or a.route_native_prefix_first\n    assert not a.route_native_prefix_first or(a.route_critical_first and a.route_residual_budget and a.negotiate_priority_routes and a.defer_access_vias)\n    assert not a.route_ordinary_zero_maze or")
sub("'ordinary_zero_maze.h','ordinary_pattern_regression.py'", "'ordinary_zero_maze.h','pin_access_reservation.h','ordinary_pattern_regression.py'")
sub('ordinary_zero_maze_budget=a.route_ordinary_zero_maze)', 'ordinary_zero_maze_budget=a.route_ordinary_zero_maze,native_prefix_first=a.route_native_prefix_first,pin_access_policy=a.route_pin_access)')
# locate argparse exact and insert
needle="    p.add_argument('--route-ordinary-zero-maze'"
line=next(l for l in s.splitlines()if needle in l)
sub(line,line+"\n    p.add_argument('--route-native-prefix-first',action='store_true')\n    p.add_argument('--route-pin-access',choices=['none','all','after-native'],default='none')")
f.write_bytes(s.encode())
