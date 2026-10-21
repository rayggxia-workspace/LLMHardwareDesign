"""Independently audit finished wave2-06 results, including worst DRV margins."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

root = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06')
spec = json.loads(Path('task.json').read_text())
record = json.loads(subprocess.check_output([sys.executable, str(Path(os.environ['LLHD_BATCH'])/'runner/wave2/status.py'), str(root)], text=True))
names = ['act-cap00', 'act-cap10', 'act-cap20']
if spec['name'] == 'full-physical-audit':
    names += ['gemm-cap10', 'gemm-cap20', 'mxu-cap20', 'merged-cap20']
rows = {}
hashes_pass = True
for name in names:
    item = record['tasks'][name]
    base = root/name
    audits = {}
    for filename in ('source-inputs.sha256', 'output-files.sha256'):
        manifest = base/filename
        if not manifest.is_file():
            audits[filename] = dict(passed=False, reason='missing manifest')
            hashes_pass = False
            continue
        with Path(name+'-'+filename+'-audit.log').open('w') as log:
            code = subprocess.run(['sha256sum', '-c', filename], cwd=base, stdout=log, stderr=subprocess.STDOUT).returncode
        audits[filename] = dict(passed=code==0, exit_code=code, entries=len(manifest.read_text().splitlines()))
        hashes_pass = hashes_pass and code==0
    q = item['quality']
    final = item['metrics'].get('6_report.json', {})
    route = item['metrics'].get('5_2_route.json', {})
    nickname = 'parallel_' + item['spec']['case'].replace('-', '_')
    report = base/'flow/reports/nangate45'/nickname/'base/6_finish.rpt'
    text = report.read_text() if report.is_file() else ''
    match = re.search(r'finish max_capacitance_check_slack\s*\n-+\s*\n([^\n]+)', text)
    worst_cap_slack = float(match[1]) if match else None
    q['worst_cap_slack_report_value'] = worst_cap_slack
    q['cap_slack_over_limit_metric'] = final.get('finish__timing__drv__max_cap_limit')
    q['setup_tns'] = final.get('finish__timing__setup__tns')
    q['hold_tns'] = final.get('finish__timing__hold__tns')
    q['antenna_nets'] = route.get('detailedroute__antenna__violating__nets')
    q['antenna_pins'] = route.get('detailedroute__antenna__violating__pins')
    def nonnegative(value):
        return isinstance(value, (int,float)) and value>=0
    gates = dict(pipeline_exit_zero=(item['exit_code'] or '').strip()=='0',
        output_hash_exit_zero=(item['hash_exit_code'] or '').strip()=='0',
        manifests_verified=all(a['passed'] for a in audits.values()), final_report='finish' in item['stages'],
        drc_zero=q['drc']==0, antenna_zero=q['antenna_nets']==0 and q['antenna_pins']==0,
        setup_nonnegative=nonnegative(q['setup_ws_ns']) and q['setup_tns']==0,
        hold_nonnegative=nonnegative(q['hold_ws_ns']) and q['hold_tns']==0,
        max_cap_count_zero=q['max_cap']==0, worst_cap_slack_nonnegative=nonnegative(worst_cap_slack),
        cap_slack_ratio_nonnegative=nonnegative(q['cap_slack_over_limit_metric']),
        slew_count_zero=q['max_slew']==0,
        slew_slack_ratio_nonnegative=nonnegative(final.get('finish__timing__drv__max_slew_limit')),
        fanout_count_zero=q['max_fanout']==0,
        fanout_slack_ratio_nonnegative=nonnegative(final.get('finish__timing__drv__max_fanout_limit')),
        abstracts_present=bool(item.get('abstracts_present')) and all(item.get('abstracts_present',{}).values()),
        vdd_reported_connected=any('All shapes on net VDD are connected' in l for l in item['final_markers']),
        vss_reported_connected=any('All shapes on net VSS are connected' in l for l in item['final_markers']),
        no_final_errors=not any('[ERROR' in l for l in item['final_markers']))
    rows[name] = dict(quality=q, checksums=audits, observed_strict_tool_gates=gates,
        observed_strict_tool_gates_pass=all(gates.values()),
        qualified_hard_macro=False, manufacturing_or_system_signoff=False,
        cap_slack_units='Raw report value; section does not declare unit')
baseline = rows['act-cap00']['quality']['instance_area_um2']
for name in ('act-cap00', 'act-cap10', 'act-cap20'):
    area = rows[name]['quality']['instance_area_um2']
    rows[name]['area_change_vs_cap00_percent'] = 100*(area-baseline)/baseline if area is not None and baseline else None
eligible = [n for n in ('act-cap00', 'act-cap10', 'act-cap20') if rows[n]['observed_strict_tool_gates_pass']]
preferred = min(eligible, key=lambda n:rows[n]['quality']['instance_area_um2']) if eligible else None
Path('validation.json').write_text(json.dumps(dict(passed=hashes_pass, kind='Artifact audit with strict physical budget observations',
    source_attempt=str(root), results=rows, source_scheduler_observation=record['scheduler'],
    preferred_act_for_further_view_qualification=preferred,
    physical_or_system_signoff=False,
    scope='Pass means manifests verified; per-case strict physical gates remain separate. Candidate selection does not qualify timing arcs, driver/load models, source-to-physical equivalence or manufacturing.'),indent=2)+'\n')
raise SystemExit(int(not hashes_pass))
