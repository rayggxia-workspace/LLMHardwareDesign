#!/bin/bash
#SBATCH --job-name=yzl-m-stream
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=UNLIMITED
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
container=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
singularity=/public/software/singularity-ce-4.3.4/bin/singularity
"$singularity" exec --cleanenv --bind /public/home/yuzelu "$container" /bin/bash -c '
 set -euo pipefail
 export PATH=/public/home/yuzelu/opt/eda/verilator-5.042/bin:$PATH
 verilator --version
 g++ --version | head -1
 for k in 16 32; do
  verilator --binary --timing --top-module tb_m_stream -GK=$k --Mdir obj_m$k -j 4 -Wall -Wno-fatal \
   source/m_s32_stream_candidate.sv source/tb_m_stream.sv > build-m$k.log 2>&1
  (cd vectors$k && ../obj_m$k/Vtb_m_stream > rtl.log 2>&1)
 done
' > native-run.log 2>&1
sha256sum source/* vectors*/m-input.txt vectors*/oracle.json > source-sha256.txt
printf 'M_NATIVE_JOB_PASS job=%s\n' "$SLURM_JOB_ID"
