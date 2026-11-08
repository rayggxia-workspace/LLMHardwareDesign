#!/usr/bin/env bash
#SBATCH --job-name=mdt-a2179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/yuzelu/Melodydt/issue179-a2-2a7f49b/r002/slurm-%j.log
set -euo pipefail
root=/public/home/yuzelu/Melodydt/issue179-a2-2a7f49b
cd "$root/r002"
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
git -C source rev-parse HEAD
sha256sum source.tar
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro \
  --bind "$root/r002:/work" --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
verilator=/eda/verilator-5.042/bin/verilator
python3 --version
python3 -B project/control_r4_v0_1/check_contract.py
python3 -B project/control_p_compute_v0_1/run_a2.py --verilator "$verilator" --out /work/results/a2
python3 -B project/control_r6_v0_1/run_campaign.py --verilator "$verilator" --out /work/results/r6
PYTHONPATH=project/control_r7_v0_1 python3 -B -c "import synthesize as s; s.CASES=[case for case in s.CASES if case[0]==\"local1\"]; s.main()" \
    --yosys /usr/local/bin/yosys \
    --openroad /eda/r166-openroad-gc-cache-2eba27b2-offline01/install/bin/openroad \
    --liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib \
    --out /work/results/lc1
'
printf 'PASS %s\n' "$(date -Is)"
