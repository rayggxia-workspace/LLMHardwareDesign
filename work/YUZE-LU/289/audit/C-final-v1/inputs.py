from pathlib import Path
import sys,re,json,hashlib
run,out,phase=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),sys.argv[3];res=next((run/'flow/results/nangate45').glob('*/*'));config=run/'config.mk'
files=[config]+[res/('6_final.'+x) for x in ('odb','sdc','spef','v','def','gds')]
for name in ('ADDITIONAL_LIBS','ADDITIONAL_GDS','ADDITIONAL_LEFS','VERILOG_FILES'):
 found=re.findall(r'^export '+name+r'\s*=\s*(.*)$',config.read_text(),re.M);assert found,name;files += [Path(x).resolve() for x in found[-1].split()]
files += [Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'),Path('/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/4_cts.odb'),Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/C-outputs.txt')]
for n in ('inputs-manifest.json','source-proof-binding.json','base-cache-proof-binding.json'):
 if (run/n).exists():files.append(run/n)
r={}
for q in files:
 h=hashlib.sha256()
 with q.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 r[str(q)]=h.hexdigest()
p=out/('inputs-'+phase+'.json');assert not p.exists();p.write_text(json.dumps(r,indent=2))
if phase=='after':assert r==json.loads((out/'inputs-before.json').read_text())
