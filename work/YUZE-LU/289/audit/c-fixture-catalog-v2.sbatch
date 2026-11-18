#!/bin/bash
#SBATCH -J yzl-C-fixturecat
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 00:10:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-fixture-catalog-v2-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/c-fixture-catalog-v2.py /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-fixture-catalog-v2.json
