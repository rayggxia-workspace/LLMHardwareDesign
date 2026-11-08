#!/usr/bin/env bash
#SBATCH --job-name=hpy-lower222
set -euo pipefail
cd "${LOWER_TASK_ROOT:?}"
output_root="$(realpath -e -- "${LOWER_OUTPUT_ROOT:-$PWD}")"
if [[ "$(dirname -- "$output_root")" != "/public/home/yuzelu/PingyangHuang" || "$(basename -- "$output_root")" != issue-222-lower-* ]]; then
  echo "Output root outside this user's lower-extraction directories" >&2
  exit 2
fi
out="$output_root/job-${SLURM_JOB_ID:?}-${SLURM_ARRAY_TASK_ID:-0}"
mkdir "$out" "$out/tmp" "$out/cache"
python3 -B - "$out/invocation.json" "$@" <<'PY'
import datetime, hashlib, json, os, pathlib, sys
root=pathlib.Path.cwd()
script=root/'project/experiments/m11_m12_rcx'/sys.argv[2]
receipt=dict(script=sys.argv[2],arguments=sys.argv[3:],source_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
             code_root=str(root),output_root=str(pathlib.Path(sys.argv[1]).parent.parent),
             source_manifest_sha256=hashlib.sha256((root/'source.json').read_bytes()).hexdigest(),
             job_id=os.environ['SLURM_JOB_ID'],array_index=os.environ.get('SLURM_ARRAY_TASK_ID','0'),
             cpus=int(os.environ['SLURM_CPUS_PER_TASK']),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with open(sys.argv[1],'x') as f:json.dump(receipt,f,indent=2);f.write('\n')
PY
export TMPDIR="$out/tmp" SINGULARITY_TMPDIR="$out/tmp" SINGULARITY_CACHEDIR="$out/cache"
export SINGULARITYENV_TMPDIR="$out/tmp" SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_LOWER_OUT="$out/result" SINGULARITYENV_LOWER_INDEX="${SLURM_ARRAY_TASK_ID:-0}"
export SINGULARITYENV_LOWER_CPUS="${SLURM_CPUS_PER_TASK:?}" SINGULARITYENV_QT_QPA_PLATFORM=offscreen
export SINGULARITYENV_OMP_NUM_THREADS=1 SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_PATH="/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:/usr/local/bin:/usr/bin:/bin"
export SINGULARITYENV_LOWER_TASK_ROOT="$PWD"
export SINGULARITYENV_LOWER_CONFIG="${LOWER_CONFIG:-$PWD/work/huangpingyang04-lgtm/222/lower-rc/lower-inputs.json}"
if [[ "$1" == *.klayout.py ]]; then
  exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" \
   /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
   klayout -b -r "project/experiments/m11_m12_rcx/$1"
else
  exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" \
   /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
   python3 -B "project/experiments/m11_m12_rcx/$1" "${@:2}"
fi
