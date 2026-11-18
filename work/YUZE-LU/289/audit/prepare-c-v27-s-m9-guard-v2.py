from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit')
p=r/'C-v27-s-m9-guard-v2';p.mkdir(exist_ok=False)
old=r/'C-v27-s-m9-guard'
for name in ('hook.tcl','probe.tcl','probe.sbatch'):
 s=(old/name).read_text().replace('C-v27-s-m9-guard','C-v27-s-m9-guard-v2').replace('2723000 228140','2723000 224940')
 (p/name).write_text(s)
s=(r/'c-v27-s-m9-gds.sbatch').read_text().replace('c-v27-s-m9-gds.py','c-v27-s-m9-gds-v2.py');(r/'c-v27-s-m9-gds-v2.sbatch').write_text(s)
# Supersede the exploratory r2 receipt: its printed empty-guard flag was hard-coded.
(old/'gds-diagnostic.json').write_text('{"accepted":false,"superseded":true,"guard_is_empty_actual_material":false,"reason":"120072 shows old guard intersects actual M9 above y113.27; v2 restricts y to111.67..112.47"}\n')