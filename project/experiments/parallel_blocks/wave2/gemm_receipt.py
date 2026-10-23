"""Re-read the frozen successful GEMM log; do not rerun or rewrite the first attempt."""
import hashlib
import json
from pathlib import Path
import re

original=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-01/gemm-regression')
relative='regression.log'
manifest={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (original/'output-files.sha256').read_text().splitlines()}
raw=(original/relative).read_bytes()
digest=hashlib.sha256(raw).hexdigest()
assert manifest[relative]==digest, 'Original log changed after its task audit'
text=raw.decode(errors='replace')
previous=json.loads((original/'validation.json').read_text())
assert previous['make_exit_code']==0
rows=re.findall(r'tb_gemm\[EPILOGUE_FUSION=([01])\]:\s*(\d+) passed,\s*(\d+) failed\s*->\s*(PASS|FAIL)',text)
assert len(rows)==2 and {r[0] for r in rows}=={'0','1'} and all(r[1:]==('500','0','PASS') for r in rows)
assert 'EPILOGUE_FUSION=0 seed=1 cases=250' in text and 'EPILOGUE_FUSION=1 seed=1 cases=250' in text
Path('validation.json').write_text(json.dumps({'passed':True,'kind':'independent original GEMM execution receipt correction',
    'original_task':str(original),'original_log_sha256_verified':digest,'summary_rows':rows,
    'original_make_exit_code':0,'original_collector_task_exit_code':1,'original_collector_format_bug':True,
    'new_simulation_executed':False,'original_runtime_cases':1000,
    'scope':'Original RTL regression passed; this new job only verifies its frozen log, no netlist equivalence or physical rerun'},indent=2)+'\n')
