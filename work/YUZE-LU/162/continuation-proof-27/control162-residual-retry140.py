import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';native=c/'native-sta/receipt.json';audit=c/'native-sta/native-system-audit.json';r=json.loads(native.read_text());assert r['execution_passed']and r['typed_native_timing_passed']and json.loads(audit.read_text())['passed'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert r['outputs']['native-system-audit.json']==sha(audit)
f=b/'dynamic-05/node4/pending/00-o-sready140-residual-after-final-receipt-1391.json';out=c/'native-cap-residual-02';record=b/'route-selection-102/sready140-residual1391-after-final-receipt.json';assert not f.exists()and not out.exists()and not record.exists()
old=b/'dynamic-05/node4/pending/00-n-sready140-residual-1391.json';spec=json.loads(old.read_text());args=spec['args'];args[args.index('--out')+1]=str(out)
spec['requires']=[str(audit),str(c/'cap-candidates/1404/receipt.json'),str(c/'cap-candidates/1405/receipt.json')]
tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(f);record.write_text(json.dumps(dict(time=time.time(),old_spec=str(old),old_spec_sha256=sha(old),new_spec=str(f),new_spec_sha256=sha(f),completed_native_receipt=str(native),completed_native_receipt_sha256=sha(native),all_original_math_and_gates_unchanged=True,reason='Original diagnostic emitted passed native audit before completing large-output receipt hashing. First residual started before receipt existed and failed I/O, not capacitance. Native execution, typed timing and complete final receipt now verified actual; append a unique retry without editing old specs/results. Original passed=false whole-system diagnostic flag remains unchanged.'),indent=2));print('Appended actual post-completion residual retry',f)
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
