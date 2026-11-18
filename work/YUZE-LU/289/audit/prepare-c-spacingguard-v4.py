from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-upper-spacing-guard-v3';p=r/'audit/C-upper-spacing-guard-v4';p.mkdir(exist_ok=False)
for n in ('export.tcl','run.sbatch'):(p/n).write_text((old/n).read_text().replace('C-upper-spacing-guard-v3','C-upper-spacing-guard-v4'))
s=(old/'derive.py').read_text().replace('import pya,json,hashlib,collections','import pya,json,hashlib,collections,math')
s=s.replace("round((a-o['dx_um']-1)*10000)","5*math.floor((a-o['dx_um']-1)*2000)").replace("round((b-o['dy_um']-1)*10000)","5*math.floor((b-o['dy_um']-1)*2000)").replace("round((c-o['dx_um']+1)*10000)","5*math.ceil((c-o['dx_um']+1)*2000)").replace("round((d-o['dy_um']+1)*10000)","5*math.ceil((d-o['dy_um']+1)*2000)")
s=s.replace('keepout=(expanded-obs-pins).merged()','keepout=((expanded-obs-pins)&pya.Region(pya.Box(0,0,sizes[n][0]*5,sizes[n][1]*5))).merged()').replace('assert all(z%5==0 for z in v);','assert all(z%5==0 for z in v),(n,layer,v);')
(p/'derive.py').write_text(s)
