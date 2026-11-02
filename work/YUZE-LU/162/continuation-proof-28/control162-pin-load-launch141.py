import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';source=b/'source-141';record=b/'route-selection-102/sready141-native-pin-load.json';assert not record.exists()
manifest=json.loads((source/'source-manifest.json').read_text());assert manifest['commit']=='4dc87e547d43cac5647a260577298f5cb7a4c9e0'
out=c/'native-pin-load-01';f=b/'dynamic-02/node26/pending/00-q-sready141-native-pin-load.json';assert not f.exists()and not out.exists()
spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=64,requires=[str(c/'capacity-native-residual-01/receipt.json'),str(c/'selected/receipt.json'),str(c/'topology/receipt.json')],args=list(map(str,['--manifest',c/'selected/physical.json','--graph',c/'topology/boundary-graph.json','--native-pin-load-residual',c/'capacity-native-residual-01/native-cap-residual.json','--out',out])))
temp=f.with_suffix('.tmp');temp.write_text(json.dumps(spec));temp.rename(f)
record.write_text(json.dumps(dict(time=time.time(),spec=str(f),spec_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_manifest_sha256=hashlib.sha256((source/'source-manifest.json').read_bytes()).hexdigest(),scope='Read-only actual final ODB boundary input inventory and minimum Liberty pin capacitance, added to actual existing native/wire necessary diagnostics. Same hardware, all searches preserved, all real gates unchanged; no qualification granted.'),indent=2));print('Appended',f)
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
