from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v27-physical';s=(r/'audit/C-main-clock4-physical-v1/map-after.sbatch').read_text().replace('C-main-clock4-physical-v1','C-v27-physical').replace('C-v20-native-clock4','C-v27-joint-e20-h30');(p/'map-after.sbatch').write_text(s)
