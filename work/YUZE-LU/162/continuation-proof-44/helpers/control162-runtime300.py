import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import time,subprocess
for name in ['r256-composition-273/function','r256-composition-274/native-sta']:
 p=b/name;print(name,[(x.name,x.stat().st_size,round(time.time()-x.stat().st_mtime,1))for x in p.iterdir()if x.is_file()and(x.suffix in ['.log','.json','.spef','.v','.tcl']or 'partial'in x.name)][-12:])
 for x in p.glob('initial-*.json'):print(x.name,x.read_text()[:700])
print(subprocess.check_output(['squeue','--steps','-j','96297','-h','-o','%i|%j|%M|%C'],universal_newlines=True))
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
