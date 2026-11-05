import subprocess,shlex
q=r'''from pathlib import Path
import subprocess,json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'dynamic-06/node7';print('SLURM',subprocess.check_output(['sacct','-j','96221','--format=JobID,JobName,State,ExitCode,Elapsed,Timelimit,MaxRSS','-P'],universal_newlines=True));print('controller tail',(p/'slurm.log').read_text().splitlines()[-22:]);print('result',[(str(f.name),f.read_text()[:1000])for f in p.glob('queue-result.json')]);print('submission',(p/'submission.json').read_text()[:1400])
'''
compile(q,'controller268','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
