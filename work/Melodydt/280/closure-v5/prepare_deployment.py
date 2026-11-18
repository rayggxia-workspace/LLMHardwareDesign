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
        'expert_routes','history_payload','history_beats','history_source_sha256','ffn_by_target',
        'expert_down_by_target','plan_sha256','model','weight_window','pr272_profile')
    invalid = [key for key in invariant_keys if result.get(key) != frozen.get(key)]
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
path.write_text(text)
receipt=dict(source=str(source),variant=variant,source_commit=(bundle/'source-commit.txt').read_text().strip(),
             accepted_runner_sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in (source/'runner').glob('*.py')},
             runner_sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in runner.glob('*.py')})
(out/'provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('DEPLOYMENT_PREPARED',variant,flush=True)
