from pathlib import Path
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu')
src=p/'runs/U-v15-guardant-f67-h3-u1.2/flow/results/nangate45/u-overlay-current/base/6_final.def'
lines=src.read_text().splitlines();active=False;out=[]
for line in lines:
 if line.lstrip().startswith('- datapath.legacy_rsp_data\\[90\\] '):active=True
 if active:
  out.append(line)
  if line.strip().endswith(';'):break
assert out and out[-1].strip().endswith(';')
(p/'u-v15-net90.defpart').write_text('\n'.join(out)+'\n')
print(len(out),'lines')