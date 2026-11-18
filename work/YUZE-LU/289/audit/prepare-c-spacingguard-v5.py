from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-upper-spacing-guard-v4';p=r/'audit/C-upper-spacing-guard-v5';p.mkdir(exist_ok=False)
for n in ('export.tcl','run.sbatch','hook.tcl'):(p/n).write_text((old/n).read_text().replace('C-upper-spacing-guard-v4','C-upper-spacing-guard-v5'))
s=(old/'derive.py').read_text().replace("for m in loc:\n if len(m['macro'])", "for m in loc:\n if m['macro']==['local_s_base'] and any(h['net'].replace(chr(92),'') in ('dma_s_rsp_data[14]','dma_s_rsp_data[52]') for h in m['hits']):unaddressed.append(m);continue\n if len(m['macro'])")
s=s.replace('Port-exempt and exterior sites still require actual postroute recheck.','S rsp14/52 pin-notch sites excluded entirely to avoid pin rings; only unrelated net54927 S site included. Port-exempt and exterior sites still require actual postroute recheck.')
(p/'derive.py').write_text(s)
