from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent
q="from pathlib import Path;import json;print(json.loads(Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-451/source-manifest.json').read_text())['commit'])"
commit=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True).strip();assert commit=='8ca13962e0c9f6d3937b07e41f821cc74ef1cc1f'
q=(h/'control162-deliver433.py').read_text(encoding='utf-8').replace('continuation-proof-51','continuation-proof-57').replace('r256-current-program-events-412','r256-padding-program-events-473').replace('r256-current-program-event-audit-422','r256-padding-program-event-audit-480').replace('program-events-reset53-433','program-events-padding453-536').replace('program-event-delivery-current433','program-event-delivery-padding453-current536').replace('continuation-proof-48/r256-reset53-final-function-audit-392','continuation-proof-55/final-program-supplement/r256-padding-final-function-audit-472').replace('state-ownership-current396.json','state-ownership-candidate453-binding.json').replace('2f3e32b35cb5a2427f22b6af806a3ecaef9db8ef',commit).replace('from current345instance final-cell programs','from actual candidate453 padding-only current345instance final-cell programs')
compile(q,'deliver536','exec');exec(compile(q,'deliver536','exec'))
