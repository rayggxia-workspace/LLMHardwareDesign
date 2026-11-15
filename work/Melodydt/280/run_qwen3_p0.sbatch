#!/usr/bin/env bash
#SBATCH --job-name=mdt-280p0
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=12
#SBATCH --time=06:00:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
bundle=$PWD
root=/public/home/yuzelu
runs=$root/Melodydt/runs
pilot=$runs/issue-280/ddr-pilot-02
old=$pilot/pilot-116481
frozen=$old/staged/replay
control=$frozen/run-116481
audit=$runs/issue-274/three-p-audit-01
new=$bundle/ab-$SLURM_JOB_ID
mkdir "$new"
sha256sum -c bundle.sha256
sha256sum --quiet -c "$pilot/audit-116481-116496/pilot-results.sha256"
sha256sum --quiet -c "$old/pilot-inputs.sha256"
sha256sum --quiet -c "$control/output.sha256"
(cd "$frozen" && sha256sum --quiet -c source.sha256 && sha256sum --quiet -c upstream.sha256)
(cd "$audit" && sha256sum --quiet -c source.sha256)
cp "$frozen"/*.py "$frozen"/*.cpp "$frozen"/fast_qwen3_short.sbatch "$frozen"/upstream.sha256 "$new/"
python3 -B stage_qwen3_p0.py "$new"
(cd "$new" && sha256sum ./*.py ./*.cpp fast_qwen3_short.sbatch > source.sha256)
sha256sum "$bundle/bundle.sha256" "$bundle/source-commit.txt" "$frozen/source.sha256" \
    "$new/source.sha256" "$old/ddr-probe.so" "$old/staged/dramsim3/libdramsim3.so" \
    "$pilot/audit-116481-116496/pilot-results.sha256" > "$new/ab-inputs.sha256"
(
    export SLURM_SUBMIT_DIR="$new" MDT_280_DDR_LIBRARY="$old/ddr-probe.so"
    export MDT_280_FFN_P0_ONLY=1 MDT_274_THREE_P=1 MDT_274_NATIVE_MATH=1 MDT_274_TRACE_LAYERS=1
    export MDT_274_RUN_SUFFIX='' MDT_274_VERIFY_MATH=0 MDT_274_GEMMA_WIDE_RESIDUAL=0
    bash "$new/fast_qwen3_short.sbatch" qwen3 prefill:4:tile128:combined decode-live:4:tile128:combined
)
candidate=$new/run-$SLURM_JOB_ID
sha256sum -c "$candidate/output.sha256"
srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$root" \
    "$root/opt/eda/containers/orfs-current-repacked.sif" env \
    LD_LIBRARY_PATH="$root/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001" \
    PYTHONPATH="$audit" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
    "$root/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python" -B \
    "$bundle/compare_qwen3_p0.py" "$control" "$candidate" \
    "$runs/issue-274/reference-workloads-01/ref-114294/qwen3" \
    "$runs/issue-274/three-p-full-01/fp32-115617-qwen3" > "$new/ab-results.json"
sha256sum "$new/ab-results.json" "$new/ab-inputs.sha256" "$candidate/output.sha256" > "$new/ab-results.sha256"
sha256sum -c "$new/ab-results.sha256"
