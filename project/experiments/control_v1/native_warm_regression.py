"""Source-bound warm M11/M12 seeds; real full-route and rejection controls."""
from pathlib import Path
import hashlib
import json
import subprocess
from pin_release_regression import run as release_run, parse
from tree_router_cpp import route


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(config, out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    previous=Path(cfg['previous_release']);old=json.loads((previous/'receipt.json').read_text())
    assert old['passed'] and old['stage']=='pin-reservation-release-focused-regression-only'
    parent=Path(next(k for k in old['inputs']if k.endswith('/system_upper.py'))).parent
    assert sha(parent/'pin_release_regression.py')==sha(Path(__file__).with_name('pin_release_regression.py'))
    reused=release_run(cfg['release_config'],out/'unchanged-release');assert reused['passed']
    for case in ('same-prefix-release-proxy','refresh8-release-mixed'):
        for suffix in ('','.native-prefix.log','.native-prefix-paths.txt','.pin-access.json'):
            assert Path(str(previous/'pin-release'/case/'router-output.txt')+suffix).read_bytes()==Path(str(out/'unchanged-release'/case/'router-output.txt')+suffix).read_bytes()
        assert(previous/'pin-release'/case/'router.log').read_bytes()==(out/'unchanged-release'/case/'router.log').read_bytes()
    original=out/'unchanged-release/same-prefix-release-proxy/router-input.txt'
    prefix=out/'unchanged-release/same-prefix-release-proxy/router-output.txt.native-prefix-paths.txt'
    manifest=out/'seed.json';manifest.write_text(json.dumps(dict(prefix=str(prefix),prefix_sha256=sha(prefix),input=str(original),input_sha256=sha(original))))
    h,tm,lm=parse(original.read_text());assert h[:4]==[24,24,24,971]
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits=lm,negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest)
    positives=[]
    for seed in (977,979):
        target=out/('full-'+str(seed));target.mkdir()
        _,proof=route(tm,24,24,seed,80,target,**kwargs)
        p=proof['native_prefix_proof']
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
        assert not p['prefix_is_frozen']and p['final_native_paths_changed']>0 and p['stage']['native_rounds']==1
        assert p['seed']['body_byte_exact']and p['initial_independent']['all_wire_budgets_verified']
        positives.append(dict(seed=seed,proof=proof))
    binary=out/'full-977/router';input_path=out/'full-977/router-input.txt'
    flags=['--critical-first','--native-prefix-first','--pin-access=none','--native-prefix-flexible']
    rejected=[]
    def reject(name,flags_,input_=input_path):
        target=out/('invalid-'+name)
        p=subprocess.run([str(binary),str(input_),str(target),*flags_],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode and not target.exists(),name
        rejected.append(dict(case=name,returncode=p.returncode,stderr=p.stderr.decode(),no_final_output=True))
    for name,extra in [('context',['--native-prefix-flexible']),('seed-context',['--native-prefix-input='+str(prefix)]),('proxy-context',flags+['--pin-access=ordinary-first']),('duplicate',flags+['--native-prefix-flexible'])]:reject(name,extra)
    lines=prefix.read_text().splitlines()
    mutations={
        'count':(0,'7'),
        'name':(1,'alien 2'),
        'branches':(1,'n0 1'),
        'driver':(2,'1 13 10 0'),
        'outside':(2,'1 0 10 0'),
        'edge':(3,'2 7 14 0 12 10 0'),
        'repeated':(3,'3 7 14 0 7 14 0 12 10 0'),
        'missing-sink':(3,'1 12 10 0'),
    }
    for name,(line,text)in mutations.items():
        changed=list(lines);changed[line]=text;path=out/('seed-'+name+'.txt');path.write_text('\n'.join(changed)+'\n')
        reject('seed-'+name,flags+['--native-prefix-input='+str(path)])
    trailing=out/'seed-trailing.txt';trailing.write_text(prefix.read_text()+'unexpected\n');reject('seed-trailing',flags+['--native-prefix-input='+str(trailing)])
    impossible=out/'seed-budget-input.txt';rows=input_path.read_text().splitlines();fields=rows[1].split();fields[-1]='1';rows[1]=' '.join(fields);impossible.write_text('\n'.join(rows)+'\n');reject('original-budget',flags+['--native-prefix-input='+str(prefix)],impossible)
    # The imported native-zero seed never grants success for a failing global search.
    failed=out/'native-pass-global-fail';failed.mkdir()
    try:route(tm,24,24,971,80,failed,**kwargs)
    except subprocess.CalledProcessError:
        assert not(failed/'router-output.txt').exists()
        log=(failed/'router.log').read_text();assert '"native_prefix_stage_passed":true'in log and log.splitlines()[-1]=='negotiation did not converge'
    else:raise AssertionError('Expected full-search rejection was accepted')
    for name,key,value in [('hash','prefix_sha256','0'*64),('input-hash','input_sha256','0'*64)]:
        changed=json.loads(manifest.read_text());changed[key]=value;path=out/('manifest-'+name+'.json');path.write_text(json.dumps(changed));target=out/('python-'+name);target.mkdir();args=dict(kwargs);args['native_prefix_input']=path
        try:route(tm,24,24,977,80,target,**args)
        except AssertionError:assert not(target/'router-output.txt').exists();rejected.append(dict(case='python-'+name,no_final_output=True))
        else:raise AssertionError('Invalid seed identity accepted')
    inputs=dict(reused['inputs'])
    for path in (config,Path(cfg['release_config']),previous/'receipt.json',Path(__file__),Path(__file__).with_name('tree_router.cpp'),Path(__file__).with_name('tree_router_cpp.py'),Path(__file__).with_name('native_prefix_seed.h')):inputs[str(path)]=sha(path)
    for path in out.rglob('*'):
        if path.is_file()and path.name not in ('router','router.exe'):inputs[str(path)]=sha(path)
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='native-warm-focused-regression-only',scope='Actual full routes with movable finite-budget upper native wires; strict seed validation, old release/refresh/71-case byte replays; no physical qualification inferred.',inputs=inputs,unchanged_release_receipt=dict(path=str(out/'unchanged-release/receipt.json'),sha256=sha(out/'unchanged-release/receipt.json'),old71_actual_replays=True,release2_actual_bytes_exact=True),full_route_positives=positives,rejected=rejected,native_zero_global_failure_rejected=True)
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
