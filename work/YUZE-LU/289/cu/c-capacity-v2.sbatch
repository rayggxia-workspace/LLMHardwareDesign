#!/bin/bash
#SBATCH -J yzl-289-C-cap0
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH --time=02:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-cap0-%j.log
exec bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/run-c-capacity-v2.sh capacity 0.0