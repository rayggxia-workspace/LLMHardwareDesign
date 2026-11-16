#!/bin/bash
#SBATCH --job-name=yzl-syn-canon
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum *.py *.sbatch "$2" > input.sha256
"$python" -m unittest discover -v -p 'test_*.py' > tests.log 2>&1
"$python" - "$2" <<'PY'
import json,sys
from collections import Counter
from frontend import import_onnx
from canonicalize import canonicalize
m=import_onnx(sys.argv[1]);n=canonicalize(m)
open('canonical.json','w').write(json.dumps(n,indent=2)+'\n')
summary={'before':len(m['tasks']),'after':len(n['tasks']),
         'recognized':dict(Counter(r['op'] for r in n['canonicalization_trace'])),
         'remaining_ops':dict(Counter(t['op'] for t in n['tasks'])),'source_sha256':m['sha256'],
         'scope':'semantic graph recognition only; not native numeric or whole-model scheduling acceptance'}
open('summary.json','w').write(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
PY
sha256sum tests.log canonical.json summary.json > output.sha256
