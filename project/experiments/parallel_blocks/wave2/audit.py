"""One-shot audit after all three streams, preserving negative quality results."""
import json
import os
from pathlib import Path
import subprocess
import sys
from quality_gates import electrical_gates, report_cap_slack

root=Path(os.environ['LLHD_BATCH'])
assert not (root/'completion.json').exists()
record=json.loads(subprocess.check_output([sys.executable,str(root/'runner/wave2/status.py'),str(root)],universal_newlines=True))
failures=0
for name,item in record['tasks'].items():
    base=root/name
    audits={}
    for filename in ('source-inputs.sha256','output-files.sha256'):
        manifest=base/filename
        if not manifest.is_file():
            audits[filename]={'status':'missing'};failures+=1;continue
        with (root/(name+'-'+filename+'-audit.log')).open('w') as log:
            code=subprocess.run(['sha256sum','-c',filename],cwd=str(base),stdout=log,stderr=subprocess.STDOUT).returncode
        audits[filename]=dict(status='pass' if code==0 else 'fail',exit_code=code,entries=len(manifest.read_text().splitlines()))
        failures+=int(code!=0)
    item['checksum_audits']=audits
    if item['spec']['kind'] in ('physical', 'route-repair'):
        q=item['quality'];markers=item['final_markers']
        nickname='parallel_'+item['spec']['case'].replace('-','_')
        report=base/'flow/reports/nangate45'/nickname/'base/6_finish.rpt'
        report_text=report.read_text() if report.is_file() else ''
        q['worst_cap_slack_report_value']=report_cap_slack(report_text)
        gates={'pipeline_exit_zero':(item['exit_code'] or '').strip()=='0',
            'hash_exit_zero':(item['hash_exit_code'] or '').strip()=='0',
            'final_report':'finish' in item['stages'],'drc_zero':q['drc']==0,
            'setup_nonnegative':isinstance(q['setup_ws_ns'],(float,int)) and q['setup_ws_ns']>=0,
            'hold_nonnegative':isinstance(q['hold_ws_ns'],(float,int)) and q['hold_ws_ns']>=0,
            'max_cap_zero':q['max_cap']==0,'max_slew_zero':q['max_slew']==0,'max_fanout_zero':q['max_fanout']==0,
            'abstracts_present':bool(item.get('abstracts_present')) and all(item.get('abstracts_present',{}).values()),
            'vdd_connected_reported':any('All shapes on net VDD are connected' in l for l in markers),
            'vss_connected_reported':any('All shapes on net VSS are connected' in l for l in markers),
            'no_final_error':bool(markers) and not any('[ERROR' in l for l in markers)}
        gates.update(electrical_gates(q, item['metrics'].get('6_report.json',{}),
            item['metrics'].get('5_2_route.json',{}), report_text))
        item['observed_tool_gates']=gates
        item['observed_tool_gates_pass']=all(gates.values())
    else:
        item['declared_validation_pass']=item.get('validation',{}).get('passed',False) and (item['exit_code'] or '').strip()=='0'
    item['manufacturing_or_system_signoff']=False
record['artifact_audit_failures']=failures
record['scope']='One-shot new artifact verification; individual validations and tool budgets retain separate scope and failures'
(root/'completion.json').write_text(json.dumps(record,indent=2)+'\n')
print('Artifact audit failures:',failures)
for name,item in record['tasks'].items():print(name,item.get('quality',item.get('validation',{}).get('passed')))
raise SystemExit(int(bool(failures)))
