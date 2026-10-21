"""Regression against frozen seven-case evidence, including ACT10's zero-count failure."""
import json
from pathlib import Path
from quality_gates import electrical_gates, nonnegative, report_cap_slack

results = Path(__file__).resolve().parent.parent/'results'
physical = json.loads((results/'parallel-blocks-wave2-06-completion.json').read_text())['tasks']
strict = json.loads((results/'parallel-blocks-wave2-11-completion.json').read_text())['tasks']['full-physical-audit']['validation']['results']
accepted = set()
for name, item in physical.items():
    slack = strict[name]['quality']['worst_cap_slack_report_value']
    report = 'finish max_capacitance_check_slack\n----------\n'+str(slack)+'\n'
    final = item['metrics']['6_report.json']
    route = item['metrics']['5_2_route.json']
    gates = electrical_gates(item['quality'], final, route, report)
    if all(gates.values()):
        accepted.add(name)
    if name == 'act-cap10':
        assert item['quality']['max_cap'] == 0
        assert not gates['worst_cap_slack_nonnegative']
assert accepted == {'act-cap20', 'gemm-cap20', 'mxu-cap20'}, accepted
assert report_cap_slack('missing') is None
assert report_cap_slack('finish max_capacitance_check_slack\n-----\nnot a number\n') is None
assert not nonnegative(None) and not nonnegative(float('nan')) and not nonnegative(float('inf'))
assert nonnegative(0) and not nonnegative(-1e-10)
print('PASS: frozen seven-case electrical gates; ACT10 rejected despite zero count; missing/nonfinite margins rejected')
