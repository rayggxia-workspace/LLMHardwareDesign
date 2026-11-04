from pathlib import Path
import json
h=Path(__file__).parent;b='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162';fixed=(h/'control162-release-fixture946/input-971.txt').read_text(encoding='utf-8');cfg=dict(baseline=b+'/r256-native-batch-regression-902',previous_refresh=b+'/r256-native-refresh-regression-927',fixture_input=fixed)
(h/'control162-config948.json').write_bytes((json.dumps(cfg,indent=2)+'\n').encode())
s=(h/'control162-queue927.py').read_text(encoding='utf-8').replace('source-926','source-947').replace('r256-native-refresh-regression-927','r256-pin-release-regression-948').replace('sready927-native-refresh-controls','sready948-pin-release-controls').replace('00-p-sready927-native-refresh-regression','00-q-sready948-pin-release-regression')
s=s.replace("'--native-refresh-regression-baseline',str(b/'r256-native-batch-regression-902')", "'--pin-release-regression-config',str(b/'config948.json')")
s=s.replace("str(b/'r256-native-batch-regression-902/receipt.json'),str(b/'r256-maze-legacy45-byte-audit-907/receipt.json'),str(b/'r256-directional-bidirectional-active-pool-audit-918/receipt.json')", "str(b/'r256-native-refresh-regression-927/receipt.json'),str(b/'r256-native-refresh-source-audit-934/receipt.json')")
compile(s,'queue948','exec');(h/'control162-queue948.py').write_bytes(s.encode());print('prepared948 config/queue')
