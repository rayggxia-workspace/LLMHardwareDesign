import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
def stage(p):
 r=p/'receipt.json'
 if r.exists():return dict(passed=json.loads(r.read_text()).get('passed'))
 f=p/'full-deck.log'
 if not f.exists():return None
 tail=f.read_text().splitlines();completed=[(x,tail[i+1].strip())for i,x in enumerate(tail)if x.startswith(chr(34)+'output'+chr(34)+' in:')and i+1<len(tail)];return dict(last_completed_output=completed[-1]if completed else None,operation=next((x for x in reversed(tail)if'in: FreePDK45'in x),tail[-1]if tail else''),operation_seconds=round(time.time()-f.stat().st_mtime))
def status(p):
 r=p/'receipt.json';return json.loads(r.read_text()).get('passed')if r.exists()else None
q=b/'s-escape-qualified-03/1350';c=b/'s-escape-composition-03/1350'
print(json.dumps(dict(native_drc=stage(b/'s-escape-gates-01/1350/drc'),pg_drc=stage(b/'s-escape-pg-compute-01/1350/wrapper'),qualification={x:status(q/x)for x in ['native','pg-wrapper','pg-physical','pg-timing','pg-delivery']},composition={x:status(c/x)for x in ['selected','topology-audit','final-composition','native-sta','pg-preflight','cap-preflight','native-cap-residual']},upper_created=(b/'route-selection-102/s1350-upper-routes-source137.json').exists())))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
