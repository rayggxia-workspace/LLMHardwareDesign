"""Fingerprint exact standalone STA/formal inputs before and after independent work."""
from pathlib import Path
import sys,re,json,hashlib
run,out,phase=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),sys.argv[3]
res=next((run/'flow/results/nangate45').glob('*/*'));config=run/'config.mk'
paths=[config]+[res/('6_final.'+x) for x in ('odb','sdc','spef','v','def','gds')]
paths+=[Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'),Path('/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/U/flow/results/nangate45/u-overlay-current/base/4_cts.odb')]
for var in ('ADDITIONAL_LIBS','ADDITIONAL_GDS','ADDITIONAL_LEFS'):
 found=re.findall(r'^export '+var+r'\s*=\s*(.*)$',config.read_text(),re.M);assert found,var
 paths += [Path(p).resolve() for p in found[-1].split()]
result={}
for p in paths:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for buf in iter(lambda:f.read(1024*1024),b''):h.update(buf)
 result[str(p)]=h.hexdigest()
p=out/('inputs-'+phase+'.json');assert not p.exists();p.write_text(json.dumps(result,indent=2))
if phase=='after':assert result==json.loads((out/'inputs-before.json').read_text()),'Inputs changed during independent qualification'
