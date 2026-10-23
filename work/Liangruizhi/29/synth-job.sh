#!/bin/bash
#SBATCH --job-name=lrz-portsyn
#SBATCH --partition=debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
set -euo pipefail
cd /public/home/yuzelu/RuizhiLiang/issue29-port-rtl-20261022/formal01
mkdir synth-check
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --contain --bind "$PWD:/work" --bind /public/home/yuzelu/opt/eda:/eda:ro /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif bash /work/synth-check.sh
