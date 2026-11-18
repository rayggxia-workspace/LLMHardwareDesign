from pathlib import Path
import json
p=Path(__file__).parent
r=json.loads((p/'c-v17-hold-endpoints.json').read_text())
s='set targets {\n'+''.join(' {{'+x['endpoint']+'} '+str(x['slack'])+'}\n' for x in r)+'}\n'
(p/'c-v17-hold-targets.tcl').write_text(s,newline='\n')