from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-main-clock4-physical-v1';p=r/'audit/C-v27-physical'
s=(old/'localize.py').read_text().replace('C-main-clock4-physical-v1','C-v27-physical').replace('C-v20-native-clock4','C-v27-joint-e20-h30');(p/'localize.py').write_text(s)
q=p/'net-localization';q.mkdir(exist_ok=False)
s=(old/'net-localization/pg.tcl').read_text().replace('C-main-clock4-physical-v1','C-v27-physical').replace('C-v20-native-clock4','C-v27-joint-e20-h30');(q/'pg.tcl').write_text(s)
s=(old/'net-localization/map.py').read_text().replace('C-main-clock4-physical-v1','C-v27-physical').replace('C-v20-native-clock4','C-v27-joint-e20-h30').replace('assert len(markers)==90,len(markers)','assert len(markers)==16,len(markers)');(q/'map.py').write_text(s)
for n in ('layers.tsv','vias.tsv','bpins.tsv'):(q/n).write_bytes((p/'rcx-material-120031'/n).read_bytes())
s=(old/'net-localization/run.sbatch').read_text().replace('C-main-clock4-physical-v1','C-v27-physical').replace('openroad -no_init','klayout -b -r ../localize.py > ../localize.log 2>&1; openroad -no_init');(q/'run.sbatch').write_text(s)
