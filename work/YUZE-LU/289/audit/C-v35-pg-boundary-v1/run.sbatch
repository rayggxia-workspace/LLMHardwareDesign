#!/bin/bash
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --job-name=yzl-C35-pg-audit
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-pg-boundary-v1/job-%j.log
bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-pg-boundary-v1/run.sh
