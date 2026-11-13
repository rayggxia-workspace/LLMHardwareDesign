#!/bin/bash
#SBATCH --job-name=yl-250guard
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?set CONTROL_SOURCE_DIR}"
mkdir -p results build
export LC_ALL=C
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
sha256sum rtl/*.sv rtl.sbatch timing_summary.py > results/source.sha256
sha256sum "${SIF}" > results/container.sha256
"${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --version > results/verilator-version.txt
for target in ${CONTROL_TARGETS:-bounded_service_guard private_a_copy}; do
  case "${target}" in
    bounded_service_guard) sources=(rtl/bounded_service_guard.sv rtl/tb_bounded_service_guard.sv);;
    private_a_copy) sources=(rtl/private_a_tile_frontend.sv rtl/early_copy_3p.sv rtl/tb_private_a_copy.sv);;
    *) exit 2;;
  esac
  srun --exclusive --ntasks=1 --cpus-per-task=10 \
    "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert \
    --Wall -j 10 --top-module "tb_${target}" --Mdir "${CONTROL_SOURCE_DIR}/build/${target}" \
    "${sources[@]}" > "results/build-${target}.log" 2>&1
  pids=()
  for seed in 1 2 3 4 5 6; do
    srun --exclusive --ntasks=1 --cpus-per-task=10 \
      "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${CONTROL_SOURCE_DIR}/build/${target}/Vtb_${target}" \
      "+SEED=${seed}" "+TRACE=${CONTROL_SOURCE_DIR}/results/${target}-${seed}.csv" > "results/${target}-${seed}.log" 2>&1 &
    pids+=("$!")
  done
  status=0
  for task in "${pids[@]}"; do wait "${task}" || status=1; done
  if [ "${status}" != 0 ]; then exit "${status}"; fi
done
/usr/bin/python3.11 -B timing_summary.py --root results --output results/timing-summary.json
