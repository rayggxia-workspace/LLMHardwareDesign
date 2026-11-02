import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-escape-composition-03/1350'
f=b/'dynamic-05/node4/pending/00-j-s1350-topology-audit138.json';assert not f.exists()
spec=dict(script='topology.py',source_root=str(b/'source-138'),forecast_gib=16,requires=[str(c/'selected/receipt.json'),str(c/'topology/boundary-graph.json')],args=['--manifest',str(c/'selected/physical.json'),'--audit-existing',str(c/'topology'),'--audit-spec',str(b/'dynamic-02/node26/pending/00-h-s1350-fast137-topology.json'),'--out',str(c/'topology-audit')]);tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(f);print('Appended',f)
p=c/'native-sta/critical-first.rpt';print('CRITICAL',p.read_text()[:12000])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
