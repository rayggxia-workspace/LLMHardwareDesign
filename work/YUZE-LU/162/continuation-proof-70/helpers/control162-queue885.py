from pathlib import Path
import subprocess,shlex
q="""from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-884';assert(source/'freeze-import.json').is_file()and(source/'source-manifest.json').is_file();out=b/'r256-native-zero-regression-885';record=b/'route-selection-102/sready885-native-zero-controls';assert not record.exists();record.mkdir();name='00-n-sready885-native-zero-regression';p=b/'dynamic-03/node5/pending'/(name+'.json');assert not p.exists()and not out.exists()
spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(b/'r256-native-prefix-path-diagnostic-873/receipt.json'),str(b/'r256-native-prefix-regression-855/receipt.json')],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(b/'r256-composition-453/topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-735/project/experiments/control_v1/tree_router.cpp'),'--out',str(out)])
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=[dict(path=str(p),spec=spec)],whole_system_qualified=False),indent=2));print(json.dumps(dict(queued=True,path=str(p),source=str(source))))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
