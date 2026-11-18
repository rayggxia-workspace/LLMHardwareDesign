#!/bin/bash
#SBATCH -J yzl-289-C-probe
#SBATCH -p debug
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 2
#SBATCH --time=00:20:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/cached-probe-%j.log
bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/inspect-cached-cts.sh
