"""Resume actual-delivery collector with bounded SSH and explicit errors.

Remote EDA and existing immutable queue specifications are never touched here.
Every failed observation is recorded; only transport failures retry.
"""
from pathlib import Path
import subprocess,time,sys,json

home=Path(r'D:\Data\电路实验')
repo=home/'LLMHardwareDesign-worktrees/issue-162-control'
log=home/'control162-watch-bounded142.log'
with log.open('a',encoding='utf-8',buffering=1)as stream:
    while not(repo/'work/YUZE-LU/162/system-delivery-ready140/index.json').exists():
        result=subprocess.run([sys.executable,str(home/'control162-system-ready140.py')],
                              capture_output=True,text=True,encoding='utf-8',errors='replace')
        stream.write(json.dumps(dict(time=time.time(),returncode=result.returncode,
                                     stdout=result.stdout,stderr=result.stderr),ensure_ascii=False)+'\n')
        if result.returncode:
            transport=any(s in result.stderr.lower()for s in (
                'timed out','timeoutexpired','connection reset','connection closed',
                'connection refused','no route to host','network is unreachable'))
            if not transport:
                print('Non-transport collector failure; inspect '+str(log),flush=True)
                raise SystemExit(result.returncode)
            time.sleep(45)
        else:
            time.sleep(45)
    print('Actual joint delivery collected; inspect source-bound index and actual layout.',flush=True)
