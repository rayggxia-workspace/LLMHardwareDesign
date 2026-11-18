from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
s=(r/'audit/C-antenna-eco-v1/dry-edit.sbatch').read_text().replace('cu/runs/C-v22-access-metal1/','cu/runs/C-v20-native-clock4/').replace('out=$C_ANT_ECO_PACKAGE/dry-edit-$SLURM_JOB_ID','out=$r/audit/C-main-clock4-physical-v1/dry-edit-$SLURM_JOB_ID')
(r/'audit/C-main-clock4-physical-v1/dry-edit.sbatch').write_text(s)
