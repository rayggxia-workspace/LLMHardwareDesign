#!/usr/bin/env bash
#SBATCH --job-name=mdt-lc179c
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/yuzelu/Melodydt/issue179-control-cancel-a54cbc4/r003/slurm-%j.log
set -euo pipefail
root=/public/home/yuzelu/Melodydt/issue179-control-cancel-a54cbc4
cd "$root/r003"
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
sha256sum source.tar
cat source.json
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro --bind "$root/r003:/work" --pwd /work/source \
  /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
mkdir -p /work/results
python3 --version
g++ --version | head -n 1
/eda/verilator-5.042/bin/verilator --version
python3 -B -m unittest discover -s project/control_isa_v0_1 -p test_codec.py -q
python3 -B -m unittest discover -s project/control_contract_v0_1 -p test_contract.py -q
python3 -B -m unittest discover -s project/control_cases_v0_1 -p test_oracle.py -q
python3 -B -m unittest discover -s project/control_image_v0_1 -p test_image.py -q
python3 -B -m unittest discover -s project/control_exec_v0_1 -p test_machine.py -q
python3 -B -m unittest discover -s project/control_exec_v0_1 -p test_recovery.py -q
python3 -B -m unittest discover -s project/control_rtl_contract_v0_1 -p test_boundary.py -q
python3 -B project/control_rtl_min_v0_1/run.py --simulator verilator --verilator /eda/verilator-5.042/bin/verilator --out /work/results/baseline
python3 -B project/control_rtl_min_v0_1/run_cancel.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/cancel
'
printf 'PASS %s\n' "$(date -Is)"
