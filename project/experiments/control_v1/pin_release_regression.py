"""Actual same-prefix failure/success checks for temporary reservation release."""
from pathlib import Path
import hashlib
import json
import subprocess

from tree_router_cpp import route
from native_refresh_regression import run as refresh_run


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse(text):
    lines=text.splitlines();h=list(map(int,lines[0].split()));terminals={};limits={}
    for line in lines[1:]:
        fields=line.split();assert fields[1]=='2'
        terminals[fields[0]]=[tuple(map(int,fields[2:4])),tuple(map(int,fields[4:6]))]
        if int(fields[6])>=0:limits[fields[0]]=int(fields[6])
    return h,terminals,limits


def run(config, out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    baseline=Path(cfg['baseline']);previous=Path(cfg['previous_refresh'])
    prior=json.loads((previous/'receipt.json').read_text());assert prior['passed']and prior['stage']=='native-refresh-focused-regression-only'
    previous_child=previous/'native-refresh/receipt.json'
    assert prior['inputs'][str(previous_child)]==sha(previous_child)
    parent_source=Path(next(k for k in prior['inputs']if k.endswith('/system_upper.py'))).parent
    current=Path(__file__).parent
    assert sha(parent_source/'native_refresh_regression.py')==sha(current/'native_refresh_regression.py')
    reused=refresh_run(baseline,out/'unchanged-refresh')
    assert reused['passed']and len(reused['legacy71_actual_byte_replays'])==71
    for period in (8,16):
        old=previous/'native-refresh'/('refresh-'+str(period));new=out/'unchanged-refresh'/('refresh-'+str(period))
        for suffix in ['', '.native-prefix.log','.native-prefix-paths.txt','.pin-access.json']:
            assert Path(str(old/'router-output.txt')+suffix).read_bytes()==Path(str(new/'router-output.txt')+suffix).read_bytes()
        assert(old/'router.log').read_bytes()==(new/'router.log').read_bytes()
    fixed=cfg['fixture_input'];header,terminals,limits=parse(fixed)
    assert header[:4]==[24,24,24,971]and header[6]==8 and len(terminals)==24 and len(limits)==8
    kwargs=dict(heuristic_weight=256,locked_names=list(terminals)[:8],wire_limits=limits,
                negotiated_priority=True,defer_access_vias=True,congestion_scale=1,
                bidirectional_two_terminal=True,weighted_bidirectional=True,
                ordinary_zero_pattern=True,nonpreferred_cost=2,pareto_wire_budget=True,
                critical_first=True,native_prefix_first=True,pin_access_policy='ordinary-first',native_batch_ripup=True)
    failed=out/'same-prefix-keep-proxy';failed.mkdir()
    try:route(terminals,24,24,971,80,failed,**kwargs)
    except subprocess.CalledProcessError:
        assert not(failed/'router-output.txt').exists()
        assert(failed/'router.log').read_text().splitlines()[-1]=='disconnected bidirectional tree: n10'
    else:raise AssertionError('Fixed proxy-island fixture unexpectedly passed without release')
    passed=out/'same-prefix-release-proxy';passed.mkdir()
    _,proof=route(terminals,24,24,971,80,passed,release_pin_reservations=True,**kwargs)
    assert(failed/'router-input.txt').read_bytes()==(passed/'router-input.txt').read_bytes()
    assert(failed/'router-output.txt.native-prefix-paths.txt').read_bytes()==(passed/'router-output.txt.native-prefix-paths.txt').read_bytes()
    assert(failed/'router-output.txt.native-prefix.log').read_bytes()==(passed/'router-output.txt.native-prefix.log').read_bytes()
    assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
    release=proof['native_prefix_proof']['pin_release_trace'];assert len(release)==1 and release[0]['unwired_search_reservations_released']>0 and release[0]['actual_m11_landings_restored']==32 and release[0]['frozen_native_paths_unchanged']
    # Actual refresh + protected ordinary ports + release + full routing,
    # rather than a native-only refresh test with no ordinary traffic.
    original=baseline/'weighted-bidirectional/native-batch-negotiated-1/router-input.txt'
    h,tm,lm=parse(original.read_text());assert h[:4]==[32,32,12,899]
    tm['ordinary_extra']=[(4,26),(26,26)]
    assert sum(len(v)for v in tm.values())==len({xy for v in tm.values()for xy in v})
    mixed=out/'refresh8-release-mixed';mixed.mkdir()
    mixed_args=dict(kwargs);mixed_args.update(locked_names=list(tm)[:12],wire_limits=lm,native_refresh_period=8)
    _,mp=route(tm,32,32,899,80,mixed,release_pin_reservations=True,**mixed_args)
    assert mp['final_conflicts']==0 and mp['independent_tree_flood']and mp['independent_cross_net_occupancy']
    assert any(t['native_full_refresh']and t['removed_trees']==12 for t in mp['native_prefix_proof']['refresh_trace'])
    assert mp['native_prefix_proof']['pin_release_trace'][0]['actual_m11_landings_restored']==2
    # A different native refresh path can still leave global conflicts.
    # The real failing full search must retain no successful output.
    global_failed=out/'refresh8-release-global-failure';global_failed.mkdir()
    try:route(terminals,24,24,971,80,global_failed,release_pin_reservations=True,native_refresh_period=8,**kwargs)
    except subprocess.CalledProcessError:
        assert not(global_failed/'router-output.txt').exists()
        log=(global_failed/'router.log').read_text();assert '"native_prefix_stage_passed":true'in log and '"unwired_search_reservations_released"'in log and log.splitlines()[-1]=='negotiation did not converge'
    else:raise AssertionError('Expected native-pass/release/full-failure fixture unexpectedly passed')
    binary=passed/'router';rejected=[]
    for name,flags in [
        ('context',['--critical-first','--release-pin-reservations']),
        ('policy',['--critical-first','--native-prefix-first','--pin-access=all','--release-pin-reservations']),
        ('duplicate',['--critical-first','--native-prefix-first','--pin-access=ordinary-first','--release-pin-reservations','--release-pin-reservations']),
        ('value',['--critical-first','--native-prefix-first','--pin-access=ordinary-first','--release-pin-reservations=1'])]:
        target=out/('invalid-'+name)
        p=subprocess.run([str(binary),str(passed/'router-input.txt'),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode and not target.exists();rejected.append(dict(case=name,returncode=p.returncode,stderr=p.stderr.decode()))
    target=out/'invalid-python';target.mkdir()
    try:route({'n':[(6,6),(10,10)]},24,24,162,10,target,release_pin_reservations=True)
    except AssertionError:assert not list(target.iterdir());rejected.append(dict(case='python-context',rejected=True))
    else:raise AssertionError('Invalid release Python context accepted')
    impossible=out/'impossible-input.txt';impossible.write_text('24 24 1 162 2 256 1 1 1 1 1 0 0 1 0 2 1\nweak 2 6 6 10 6 3\n')
    target=out/'impossible-output.txt'
    p=subprocess.run([str(binary),str(impossible),str(target),'--critical-first','--native-prefix-first','--pin-access=ordinary-first','--release-pin-reservations'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert p.returncode and not target.exists()and b'disconnected finite-resource tree'in p.stderr
    rejected.append(dict(case='original-wire-budget',returncode=p.returncode,stderr=p.stderr.decode(),no_final_output=True))
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='pin-reservation-release-focused-regression-only',
                unchanged_refresh_component=dict(receipt=str(out/'unchanged-refresh/receipt.json'),sha256=sha(out/'unchanged-refresh/receipt.json'),actual_old71_replays=71,actual_refresh2_positives=2,actual_refresh6_rejections=6,previous_two_refresh_actual_bytes_exact=True),
                same_prefix_failure_to_success=dict(input_sha256=sha(passed/'router-input.txt'),native_prefix_sha256=sha(passed/'router-output.txt.native-prefix-paths.txt'),proof=proof),
                mixed_refresh_release_positive=mp,native_and_release_pass_global_failure_rejected=True,new_release_rejections=rejected,
                inputs={str(config):sha(config),str(previous/'receipt.json'):sha(previous/'receipt.json'),str(previous_child):sha(previous_child),str(parent_source/'native_refresh_regression.py'):sha(parent_source/'native_refresh_regression.py'),str(current/'tree_router.cpp'):sha(current/'tree_router.cpp'),str(current/'tree_router_cpp.py'):sha(current/'tree_router_cpp.py'),str(Path(__file__)):sha(__file__)},
                scope='Actual fixed24net971 same input and identical eight frozen native paths/log: keeping temporary proxies fails n10, releasing only unwired ordinary search reservations passes all full routes/edges/vias/flood/wire constraints. Actual mixed refresh8/ordinary-traffic/release full positive and native+release-pass/global-fail negative retain original acceptance. Six new release rejects; previous unchanged helper executes two refresh positives/71actual old byte replays/six old refresh negatives again, and its two positive artifacts match actual927 exactly. Actual M11 landings and every frozen native path retained; temporary proxies are not fabricated wires. No fullscene or physical acceptance inferred.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
