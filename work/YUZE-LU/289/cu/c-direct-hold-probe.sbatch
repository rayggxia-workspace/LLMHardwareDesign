#!/bin/bash
#SBATCH -J yzl-289-C-direct
#SBATCH -p debug,c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH --time=01:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-direct-%j.log
exec bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-direct-hold-probe.sh