"""Focused native refresh checks, reusing a source-bound complete baseline.

Default-off behavior is executed against every previous actual route, rather
than inferred from static code. No whole-scene physical acceptance is granted.
"""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import subprocess

from tree_router_cpp import route


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def folder_name(x):
    if x.get('fixture') == 'negotiated-native-batch':
        return 'native-batch-negotiated-'+str(int(x['batch']))
    return (('batch-'if x['batch']else '')+
            ('nativemaze%d-'%x['native_maze']if x['native_maze']else '')+
            ('native-'+x['pin']+'-'if x['native']else '')+
            ('maze%d-'%x['maze']if x['maze']else '')+
            ('escape-'if x['escape']else '')+('trace-'if x['tracing']else '')+
            ('window%d-'%x['margin']if x['margin']else '')+
            ('threshold%d-'%x['threshold_rounds']if x['threshold_rounds']else '')+
            'weight%d-scale%d-mode%d-cost%d-pattern%d'%(
                x['weight'],x['scale'],x['mode'],x['direction_cost'],int(x['zero_pattern'])))


def cli(proof, x):
    flags=[]
    if proof['finite_resource_label_memory_envelope']!=4000000:
        flags.append('--resource-labels='+str(proof['finite_resource_label_memory_envelope']))
    for key,flag in [('priority_partition_each_round','--critical-first'),
                     ('ordinary_zero_pattern','--ordinary-zero-pattern'),
                     ('weighted_bidirectional','--weighted-bidirectional'),
                     ('ordinary_endpoint_escape','--ordinary-endpoint-escape'),
                     ('native_batch_ripup','--native-batch-ripup')]:
        if proof[key]:flags.append(flag)
    if x.get('tracing'):flags.append('--trace-routing-phases')
    for key,flag in [('weighted_pair_margin','weighted-pair-margin'),
                     ('ordinary_threshold_pattern_rounds','ordinary-threshold-pattern-rounds'),
                     ('ordinary_zero_maze_budget','ordinary-zero-maze'),
                     ('native_zero_maze_budget','native-zero-maze')]:
        if proof[key]:flags.append('--'+flag+'='+str(proof[key]))
    if proof['native_prefix_first']:
        flags+=['--native-prefix-first','--pin-access='+proof['pin_access_policy']]
    return flags


def run(baseline, out):
    baseline=Path(baseline);out=Path(out);out.mkdir()
    old=json.loads((baseline/'receipt.json').read_text());assert old['passed']
    report=baseline/'directional-regression.json'
    assert old['outputs'][report.name]==sha(report)
    d=json.loads(report.read_text());w=d['weighted_bidirectional_cases']
    assert d['passed']and w['passed']and len(w['cases'])==71 and len(w['rejected'])==45
    old_upper=Path(next(k for k in old['inputs']if k.endswith('/system_upper.py')))
    assert sha(old_upper)==old['inputs'][str(old_upper)]
    previous=old_upper.parent;current=Path(__file__).parent;invariants=[]
    for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py',
                 'native_pin_load.py','native_cap_residual.py','upper_cap_bound.py',
                 'steiner_wire_bound.py','placement_residual_budget.py','resource_search.h',
                 'r256_scene.py','ordinary_zero_pattern.h','ordinary_endpoint_escape.h',
                 'router_trial_pool.py','test_router_trial_pool.py','weighted_bidirectional.h',
                 'ordinary_zero_maze.h','pin_access_reservation.h','weighted_bidir_regression.py']:
        assert sha(previous/name)==sha(current/name),name
        invariants.append(dict(name=name,sha256=sha(current/name)))
    a=(previous/'tree_router.cpp').read_text();z=(current/'tree_router.cpp').read_text()
    start='    if(pareto_wire_budget&&n<locked_count&&wire_limits[n]>=0){';end='    }else if(bidirectional_two_terminal'
    assert a.split(start,1)[1].split(end,1)[0]==z.split(start,1)[1].split(end,1)[0]
    assert a.split('struct BidirectionalSearch {',1)[1].split('\n};',1)[0]==z.split('struct BidirectionalSearch {',1)[1].split('\n};',1)[0]
    # Read the original fixed fixture rather than substitute newly generated
    # coordinates. The fixed source fixture is already bound by the baseline.
    fixture=baseline/'weighted-bidirectional/native-batch-negotiated-1/router-input.txt'
    lines=fixture.read_text().splitlines();header=list(map(int,lines[0].split()))
    assert header[:3]==[32,32,12]and header[3]==899
    terminals={};limits={}
    for line in lines[1:]:
        fields=line.split();assert fields[1]=='2';terminals[fields[0]]=[tuple(map(int,fields[2:4])),tuple(map(int,fields[4:6]))];limits[fields[0]]=int(fields[6])
    positives=[]
    for period in (8,16):
        target=out/('refresh-'+str(period));target.mkdir()
        _,p=route(terminals,32,32,899,80,target,heuristic_weight=256,
                  locked_names=list(terminals),wire_limits=limits,negotiated_priority=True,
                  defer_access_vias=True,congestion_scale=1,nonpreferred_cost=2,
                  pareto_wire_budget=True,critical_first=True,native_prefix_first=True,
                  pin_access_policy='ordinary-first',native_batch_ripup=True,native_refresh_period=period)
        assert p['final_conflicts']==0 and p['independent_cross_net_occupancy']and p['independent_tree_flood']
        trace=p['native_prefix_proof']['refresh_trace'];assert any(t['native_full_refresh']for t in trace)
        assert all(t['native_full_refresh']==(t['round']%period==0)and
                   (t['removed_trees']==12 if t['native_full_refresh']else 0<t['removed_trees']<=12)for t in trace)
        positives.append(dict(period=period,proof=p))
    binary=out/'refresh-8/router';assert sha(binary)==sha(out/'refresh-16/router')
    replay_root=out/'legacy71';replay_root.mkdir()
    def replay(x):
        name=folder_name(x);prior=baseline/'weighted-bidirectional'/name;target=replay_root/name;target.mkdir()
        inp=target/'input.txt';inp.write_bytes((prior/'router-input.txt').read_bytes());dest=target/'output.txt'
        flags=cli(x['proof'],x)
        with(target/'router.log').open('wb')as log:
            subprocess.run([str(binary),str(inp),str(dest),*flags],stdout=log,stderr=subprocess.PIPE,check=True)
        assert dest.read_bytes()==(prior/'router-output.txt').read_bytes()
        def filtered(p):
            return b''.join(l for l in p.read_bytes().splitlines(keepends=True)if b'routing_phase_event'not in l)
        assert filtered(target/'router.log')==filtered(prior/'router.log')
        extras=[]
        for suffix in ['.native-prefix.log','.native-prefix-paths.txt','.pin-access.json']:
            oldp=Path(str(prior/'router-output.txt')+suffix);newp=Path(str(dest)+suffix)
            assert oldp.exists()==newp.exists()
            if oldp.exists():assert filtered(oldp)==filtered(newp);extras.append(dict(suffix=suffix,sha256=sha(newp)))
        return dict(folder=name,input_sha256=sha(inp),output_sha256=sha(dest),extras=extras,flags=flags,byte_exact=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8)as pool:
        replays=list(pool.map(replay,w['cases']))
    assert len(replays)==71
    first=replay_root/folder_name(w['cases'][0]);rejected=[]
    for name,flags in [
        ('no-batch',['--critical-first','--native-prefix-first','--native-refresh=8']),
        ('no-native',['--critical-first','--native-batch-ripup','--native-refresh=8']),
        ('duplicate',['--critical-first','--native-prefix-first','--native-batch-ripup','--native-refresh=8','--native-refresh=16']),
        ('value',['--critical-first','--native-prefix-first','--native-batch-ripup','--native-refresh=32'])]:
        target=out/('invalid-'+name)
        p=subprocess.run([str(binary),str(first/'input.txt'),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode and not target.exists();rejected.append(dict(case=name,returncode=p.returncode,stderr=p.stderr.decode()))
    target=out/'invalid-python';target.mkdir()
    try:route({'n':[(6,6),(10,10)]},24,24,162,10,target,native_refresh_period=8)
    except AssertionError:assert not list(target.iterdir());rejected.append(dict(case='python-context',rejected=True))
    else:raise AssertionError('Invalid refresh Python context accepted')
    impossible=out/'impossible-input.txt';impossible.write_text('24 24 1 162 2 256 1 1 1 1 1 0 0 1 0 2 1\nweak 2 6 6 10 6 3\n')
    target=out/'impossible-output.txt'
    p=subprocess.run([str(binary),str(impossible),str(target),'--critical-first','--native-prefix-first','--native-batch-ripup','--native-refresh=8'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert p.returncode and not target.exists()and b'disconnected finite-resource tree'in p.stderr
    rejected.append(dict(case='original-wire-budget',returncode=p.returncode,stderr=p.stderr.decode(),no_final_output=True))
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,
                stage='native-refresh-focused-regression-only',positive=positives,
                legacy71_actual_byte_replays=replays,new_rejections=rejected,
                reused_prior_45_rejections=dict(path=str(baseline/'receipt.json'),sha256=sha(baseline/'receipt.json'),executed_in_previous_source_not_this_run=True),
                invariants=invariants,original_finite_and_exact_class_byte_unchanged=True,
                inputs={str(report):sha(report),str(old_upper):sha(old_upper),str(fixture):sha(fixture),
                        str(current/'tree_router.cpp'):sha(current/'tree_router.cpp'),str(current/'tree_router_cpp.py'):sha(current/'tree_router_cpp.py'),str(Path(__file__)):sha(__file__)},
                scope='Two actual fixed12native refresh8/16 routes independently check full zero-conflict edges/vias/flood/originalwire; actual full-refresh log must remove all12. One checked source-bound new binary replays all71 old real inputs, outputs, main/native logs, frozen prefixes and pin plans exactly with refresh disabled. Previous complete901/902 regression and45negative reused explicitly, not attributed to this run. Six new rejection checks and19 invariant files/original finite/exact branch verified. No fullscene, optimum, convergence guarantee or physical acceptance.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
