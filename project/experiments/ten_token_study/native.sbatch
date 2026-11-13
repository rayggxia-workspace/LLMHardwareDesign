#!/bin/bash
#SBATCH --job-name=yzl-nexp-batch
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=UNLIMITED
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}/source"
container=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
singularity=/public/software/singularity-ce-4.3.4/bin/singularity
"$singularity" exec --cleanenv --bind /public/home/yuzelu "$container" /bin/bash -c '
 set -euo pipefail
 export PATH=/public/home/yuzelu/opt/eda/verilator-5.042/bin:$PATH
 verilator --version
 g++ --version | head -1
 verilator --binary --timing --top-module tb_nexp_batch --Mdir ../obj_native -j 4 -Wall -Wno-fatal \
  +incdir+native native/block_v2_n_group.sv native/block_v2_n.sv nexp_batch_adapter.sv tb_nexp_batch.sv
 ../obj_native/Vtb_nexp_batch
' > ../native-run.log 2>&1
sha256sum *.sv native/* > ../native-source-sha256.txt
printf 'NATIVE_JOB_PASS job=%s\n' "$SLURM_JOB_ID"
