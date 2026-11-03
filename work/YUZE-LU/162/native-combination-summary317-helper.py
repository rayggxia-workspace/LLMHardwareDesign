from pathlib import Path
import subprocess,shlex,json
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import hashlib,time
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();root=b/'r256-composition-274';p=root/'native-sta';r=json.loads((p/'receipt.json').read_text());a=json.loads((p/'native-system-audit.json').read_text());assert r['outputs']['native-system-audit.json']==sha(p/'native-system-audit.json')and a['passed']and r['execution_passed'];t=a['typed']['timed_endpoints'];assert t['passed']and all(t['checks'].values());function=b/'r256-composition-273/function/receipt.json';f=json.loads(function.read_text());assert f['passed']and f['real_program_count']==8
bindings={str(x):sha(x)for x in [p/'receipt.json',p/'native-system-audit.json',p/'native-timing.json',function,root/'native-pin-load307/native-pin-load.json']}
program_inputs={k:v for k,v in f['inputs'].items()if Path(k).name in ['test_system.cpp','actual-qualified-top.v','control_system.sv']}
d=dict(passed=True,whole_system_qualified=False,scope='Compact derived review summary of actual completed native diagnostic and final-cell program gates only; does not qualify M11/M12, geometry, PG or final distributed-RC system.',capture_time=time.time(),source_sha256=bindings,native=dict(minimum_setup_ns=t['minimum_setup_ns'],minimum_hold_ns=t['minimum_hold_ns'],checks=t['checks'],native_summary=t['native_summary'],electrical=t['electrical'],endpoints=t['endpoint_count'],all_retained_endpoints_finite=not t['endpoints_without_finite_both_limits'],qualified_protection_inputs=a['typed']['qualified_passive_count']),real_programs=dict(program_count=8,initial_results=f['initial_results'],actual_final_leaf_count=f['actual_final_leaf_count'],physical_instances=f['physical_instances'],input_sources=program_inputs))
print(json.dumps(d))
'''
compile(q,'cprogress284','exec');raw=subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40);repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');out=repo/'work/YUZE-LU/162/native-combination-summary317.json';assert not out.exists();out.write_bytes(raw);d=json.loads(raw);print(json.dumps(dict(native_passed=d['passed'],whole_system_qualified=False,programs=d['real_programs']['program_count'],native_checks=d['native']['checks'])))
