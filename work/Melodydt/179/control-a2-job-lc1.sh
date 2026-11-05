#!/usr/bin/env bash
#SBATCH --job-name=mdt-a2lc1
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/yuzelu/Melodydt/issue179-a2-2a7f49b/lc1-base/slurm-%j.log
set -euo pipefail
root=/public/home/yuzelu/Melodydt/issue179-a2-2a7f49b
baseline=/public/home/yuzelu/Melodydt/issue179-r7-0429573/r002/source
cd "$root/lc1-base"
test "$(git -C "$baseline" rev-parse HEAD)" = 53a1620b9ca4a667e6e9c85cb07968d991f2d928
git -C "$baseline" diff --quiet HEAD -- project
printf 'START %s host=%s source=%s\n' "$(date -Is)" "$(hostname)" "$(git -C "$baseline" rev-parse HEAD)"
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro \
  --bind "$baseline:/baseline:ro" --bind "$root/lc1-base:/work" --pwd /baseline \
  /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
PYTHONPATH=project/control_r7_v0_1 python3 -B -c "import synthesize as s; s.CASES=[case for case in s.CASES if case[0]==\"local1\"]; s.main()" \
  --yosys /usr/local/bin/yosys \
  --openroad /eda/r166-openroad-gc-cache-2eba27b2-offline01/install/bin/openroad \
  --liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib \
  --out /work/results/lc1
'
printf 'PASS %s\n' "$(date -Is)"
