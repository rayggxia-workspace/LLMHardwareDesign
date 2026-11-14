#!/bin/bash
#SBATCH --job-name=zny-head-sample
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
root=/public/home/yuzelu/project-circuit
a=$root/issue260-product-result-vocab-xlXs1bpB/typed-vocab-105394
assets=$a/generated
memory=$root/issue234-native-fixed-skip-request-H2gY5uiN/request-memory-archived/ddr-initial.tsv
config=$root/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini
dependencies=$root/issue260-tlm-joint-9BiJdfEg
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
(cd "$a"; sha256sum -c <(grep -E '  generated/(descriptors.bin|x.hex)$' proof.sha256))
(cd tlm; sha256sum -c source.sha256 >/dev/null)
test -s tlm/run-114107.dram.so
for variant in baseline candidate; do
 srun --exact -n1 -c1 --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
  --env "PYTHONPATH=$PWD/tlm:$dependencies/systemc_benchmark:$dependencies/block_local_native" "$image" \
  python3 -B sample_head16.py tlm/source "$assets" "$memory" "$PWD/tlm/run-114107.dram.so" "$config" \
  "sample-$SLURM_JOB_ID-$variant" "$variant"
done
sha256sum sample_head16.py run_head_sample.sbatch tlm/source.sha256 "$assets/descriptors.bin" "$assets/x.hex" "$memory" \
 "$config" "$image" tlm/run-114107.dram.so sample-"$SLURM_JOB_ID"-{baseline,candidate}/profile.json > "sample-$SLURM_JOB_ID.sha256"
sha256sum -c "sample-$SLURM_JOB_ID.sha256"
