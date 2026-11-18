from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-v27-physical/oai221-isolated';p=r/'audit/C-v27-physical/oai221-x2-isolated';p.mkdir(exist_ok=False)
s=(old/'export.py').read_text().replace('OAI221_X4','OAI221_X2');(p/'export.py').write_text(s)
s=(old/'run.sbatch').read_text().replace('oai221-isolated','oai221-x2-isolated');(p/'run.sbatch').write_text(s)
