from pathlib import Path
import json
h=Path(__file__).parent;p=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1\weighted_bidir_regression.py');s=p.read_text(encoding='utf-8')
def sub(a,z):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,z,1)
sub('native_maze=0):','native_maze=0, batch=False):')
sub("folder = out / (('nativemaze", "folder = out / (('batch-'if batch else '') + ('nativemaze")
sub('native_zero_maze_budget=native_maze)', 'native_zero_maze_budget=native_maze,native_batch_ripup=batch)')
sub("if pin=='all':assert", "if pin in ('all','ordinary-first'):assert")
sub("            # Validate every proposed", "            if pin=='ordinary-first':assert plan['terminals']==sum(len(v)for k,v in terminals.items()if k not in ('weak0','weak1')) and all(n>=2 for n,v,w in plan['plan'])\n            # Validate every proposed")
sub('native_maze=native_maze,','native_maze=native_maze,batch=batch,')
fixture=json.loads((h/'control162-batch-fixture899/fixture.json').read_text());points=fixture['points'];assert fixture['seed']==899
a='    assert len(rows)==63\n    first'
z='''    assert len(rows)==63
    with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
        rows+=list(pool.map(lambda pair:case((256,1,pair[0],2,1),escape=True,maze=16384,native=True,pin='ordinary-first',native_maze=pair[1],batch=True),
                           [(mode,budget)for mode in range(3)for budget in (0,16384)]))
    # A fixed, genuinely negotiated native fixture: the enabled run must
    # remove multiple trees after round0, then pass independent full checks.
    points=POINTS
    for enabled in (False,True):
        folder=out/('native-batch-negotiated-'+str(int(enabled)));folder.mkdir()
        terminals={'n'+str(i):[tuple(points[2*i]),tuple(points[2*i+1])]for i in range(12)}
        _,proof=route(terminals,32,32,899,80,folder,heuristic_weight=256,
            locked_names=list(terminals),wire_limits={n:90 for n in terminals},
            negotiated_priority=True,defer_access_vias=True,congestion_scale=1,
            nonpreferred_cost=2,pareto_wire_budget=True,critical_first=True,
            native_prefix_first=True,pin_access_policy='ordinary-first',native_batch_ripup=enabled)
        assert proof['final_conflicts']==0 and proof['independent_cross_net_occupancy']and proof['independent_tree_flood']
        assert proof['native_prefix_proof']['frozen_prefix_matches_full_route']
        trace=proof['native_prefix_proof']['batch_trace']
        assert (any(x['native_batch_removed_trees']>=2 for x in trace)if enabled else not trace)
        rows.append(dict(fixture='negotiated-native-batch',batch=enabled,proof=proof))
    assert len(rows)==71
    first'''.replace('POINTS',repr(points));sub(a,z)
sub('    assert len(rejected)==40', '''    assert len(rejected)==40
    for label,flags in [('batch-context',['--critical-first','--native-batch-ripup']),
                        ('batch-duplicate',['--native-prefix-first','--native-batch-ripup','--native-batch-ripup']),
                        ('batch-value',['--native-prefix-first','--native-batch-ripup=2']),
                        ('ordinary-first-context',['--critical-first','--pin-access=ordinary-first'])]:
        target=out/('invalid-'+label)
        result=subprocess.run([str(first/'router'),str(good),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not target.exists()
        rejected.append(dict(case=label,rejected=True,returncode=result.returncode,stderr=result.stderr.decode()))
    folder=out/'invalid-python-native-batch';folder.mkdir()
    try:route({'net':[(6,6),(10,10)]},24,24,162,10,folder,native_batch_ripup=True)
    except AssertionError:
        assert not list(folder.iterdir());rejected.append(dict(case='python-native-batch-context',rejected=True))
    else:raise AssertionError('Native batch without staged context accepted')
    assert len(rejected)==45''')
s=s.replace('All63 actual','All71 actual').replace('All previous57 cases retained','All previous63 cases retained').replace('40 invalid/failing contexts rejected','45 invalid/failing contexts rejected');p.write_bytes(s.encode());compile(s,str(p),'exec');print('71 cases/45 negative checks configured')
