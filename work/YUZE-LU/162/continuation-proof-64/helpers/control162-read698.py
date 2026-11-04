import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');o=b/'r256-weighted-bidir-regression-691';queue=b/'dynamic-03/node5';s=json.loads((queue/'queue-state.json').read_text());print(json.dumps(dict(active=s['active'],regression_dir_exists=o.is_dir(),children=sorted(p.name for p in o.iterdir())if o.exists()else[],receipt=json.loads((o/'receipt.json').read_text())if(o/'receipt.json').exists()else None,result=json.loads((queue/'results/00-f-sready691-weighted-bidirectional-regression.json').read_text())if(queue/'results/00-f-sready691-weighted-bidirectional-regression.json').exists()else None)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
