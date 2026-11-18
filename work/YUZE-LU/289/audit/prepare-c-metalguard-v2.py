from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-upper-metal-guard-v1';new=r/'audit/C-upper-metal-guard-v2';new.mkdir(exist_ok=False)
for n in ('export.tcl','run.sbatch'):(new/n).write_text((old/n).read_text().replace('C-upper-metal-guard-v1','C-upper-metal-guard-v2'))
s=(old/'derive.py').read_text().replace('assert abs(l.dbu-0.0005)<1e-12,l.dbu','assert abs(l.dbu-0.0001)<1e-12,l.dbu; scale=5').replace('pya.Box(*map(int,v[:4]))','pya.Box(*[int(z)*scale for z in v[:4]])').replace('b.right<=size[n][0] and b.top<=size[n][1]','b.right<=size[n][0]*scale and b.top<=size[n][1]*scale').replace('rows.append((n,layer,b.left,b.bottom,b.right,b.top))','assert all(z%scale==0 for z in [b.left,b.bottom,b.right,b.top]);rows.append((n,layer,b.left//scale,b.bottom//scale,b.right//scale,b.top//scale))')
(new/'derive.py').write_text(s)
