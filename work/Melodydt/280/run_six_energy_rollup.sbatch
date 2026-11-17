#!/usr/bin/env bash
#SBATCH --job-name=mdt-280epower
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
model=${1:?model}
replay_job=${2:?accepted replay job}
case "$model" in llama|granite|phi|gemma|qwen35|falcon) ;; *) exit 2 ;; esac
[[ $replay_job =~ ^[0-9]+$ ]] || exit 2
bundle=${SLURM_SUBMIT_DIR:?}
run=$bundle/run-$replay_job-$model
out=$bundle/power-$SLURM_JOB_ID-$model
mkdir "$out"
cd "$run"
sha256sum --quiet -c results.sha256
python3 -VV > "$out/python-version.txt"
python3 -B "$bundle/six_model_tlm_power.py" "$model" "$run" "$bundle" "$out/${model}_tlm_power_v1.json"
cp "$run/source-commit.txt" "$out/replay-source-commit.txt"
cp "$bundle/rollup-source-commit.txt" "$out/rollup-source-commit.txt"
sha256sum "$bundle/six_model_tlm_power.py" "$bundle/run_six_energy_rollup.sbatch" \
    "$bundle/"qwen3_{tlm_power_v1,m_baseline_reference,s_p_macro_calibration,mother_pm_macro_calibration}.json \
    "$run/results.sha256" "$out/${model}_tlm_power_v1.json" > "$out/results.sha256"
sha256sum --quiet -c "$out/results.sha256"
echo "MODEL_POWER_REFERENCE_PASS $model replay=$replay_job power=$SLURM_JOB_ID"
