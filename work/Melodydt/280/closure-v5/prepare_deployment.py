"""Create a private continuation of an accepted operator-capture runner."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

source,bundle,out=map(Path,sys.argv[1:4]);variant=sys.argv[4]
if variant not in ('observe','e32-18'):raise ValueError('unknown variant')
out.mkdir();shutil.copytree(source/'runner',out/'runner')
for name in ('projection_math.so','qualified-windows.json','transfer-verified.json'):
    if (source/name).exists():shutil.copy2(source/name,out/name)
runner=out/'runner'
if not (runner/'run_frozen_model_energy.py').exists():
    # Qwen3's accepted capture was launched through its compiler CLI. Replay
    # its already sealed assets with the same strict numerical checker.
    root=source.parent.parent
    common=root/'operator-capture-02/run-38830188/runner'
    for name in ('run_frozen_model_energy.py','ddr_window_energy.py'):
        shutil.copy2(common/name,runner/name)
    baseline={'prefill':str(source/'prefill-w4-tile128-pr272-combined'),
              'decode':str(source/'decode-live-w4-tile128-pr272-combined')}
    windows={}
    for phase,path in baseline.items():
        result=json.loads((Path(path)/'result.json').read_text())
        if phase=='prefill':
            windows['prefill']={'start_ps':0,'end_ps':result['boundary'][1]['complete_ps']}
        else:
            first,last=[x['time_ps'] for x in result['retirements']]
            windows['first_token']={'start_ps':0,'end_ps':first}
            windows['decode']={'start_ps':first,'end_ps':last}
    (out/'qualified-windows.json').write_text(json.dumps(windows,indent=2)+'\n')
    (out/'transfer-verified.json').write_text(json.dumps({'model':'qwen3','baseline':baseline},indent=2)+'\n')
shutil.copy2(bundle/'deployment_observation.py',runner/'deployment_observation.py')
path=runner/'run_frozen_model_energy.py'
text=path.read_text()
old='from operator_observation import OperatorObservation as ModelObservation'
if text.count(old)!=1:raise ValueError('accepted observation import changed')
text=text.replace(old,'from deployment_observation import DeploymentObservation as ModelObservation')
old='observation = ModelObservation(execution)'
if text.count(old)!=1:raise ValueError('accepted observer initialization changed')
text=text.replace(old,'observation = ModelObservation(execution, calibrate=%r)'%(variant=='e32-18'))
if variant=='e32-18':
    old='    if changed:\n'
    if text.count(old)!=1:raise ValueError('acceptance code changed')
    insert='''    invariant_keys = ('mode','layers','history','calls','pages','writes_committed',
        'cross_step_reads','recurrent_writes','recurrent_cross_step_reads','residual_saturations',
        'expert_routes','history_payload','history_beats','history_source_sha256',
        'plan_sha256','model','weight_window','pr272_profile')
    invalid = [key for key in invariant_keys if result.get(key) != frozen.get(key)]
    for key in ('ffn_by_target','expert_down_by_target'):
        strip_wait = lambda rows: {site:{k:v for k,v in stats.items() if k!='weight_wait_ps'}
                                   for site,stats in (rows or {}).items()}
        if strip_wait(result.get(key)) != strip_wait(frozen.get(key)): invalid.append(key)
    for key in ('reads','writes','callbacks'):
        if result['ddr'][key] != frozen['ddr'][key]: invalid.append('ddr.'+key)
    for key in ('boundary','retirements'):
        strip = lambda rows: [{k:v for k,v in row.items() if k not in ('complete_ps','time_ps')} for row in rows]
        if strip(result[key]) != strip(frozen[key]): invalid.append(key)
    (a.output/'timing-changes.json').write_text(json.dumps(dict(changed=changed,
        baseline_interval_ps=frozen['interval_ps'], calibrated_interval_ps=result['interval_ps'],
        baseline_tok_s=frozen['tok_s'], calibrated_tok_s=result['tok_s']),indent=2)+'\\n')
    if invalid:
'''
    text=text.replace(old,insert).replace('"frozen result changed: " + str(changed)','"frozen numerical/traffic invariant changed: " + str(invalid)')
    text=text.replace('energy = evaluate(a.output, a.baseline)','energy = evaluate(a.output)')
    text=text.replace('"complete_result_equal": True','"complete_result_equal": False, "timing_calibrated": "E32 MUL 18 cycles only", "numerical_and_traffic_invariants_equal": True')
# Preserve diagnostic observations even if a downstream acceptance check fails.
# Their presence does not imply acceptance; collectors require acceptance.json
# and the successful, hash-verified results manifest.
write='    observation.write(a.output / "component-observation.json")\n'
if text.count(write)!=1:raise ValueError('observation write changed')
text=text.replace(write,'').replace('    result = execution.run(trace_layers=True)\n',
    '    result = execution.run(trace_layers=True)\n'+write)
path.write_text(text)
receipt=dict(source=str(source),variant=variant,source_commit=(bundle/'deployment-source-commit.txt').read_text().strip(),
             accepted_runner_sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in (source/'runner').glob('*.py')},
             runner_sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in runner.glob('*.py')})
(out/'provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('DEPLOYMENT_PREPARED',variant,flush=True)
