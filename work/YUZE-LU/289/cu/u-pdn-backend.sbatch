#!/bin/bash
#SBATCH -J yzl-289-u-pdn
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=08:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-pdn-backend-%j.log
set -euo pipefail
exec bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/run-u-pdn-backend.sh
