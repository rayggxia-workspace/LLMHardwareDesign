#!/bin/bash
#SBATCH --job-name=yzl-tile-plan
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
sha256sum *.py *.cpp "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9"/*.hpp > input.sha256
mkdir proof
tar -xzf "$4" -C proof probes/column-v3-profile probes/probe-v5-profile
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
"${sim[@]}" g++ -std=c++17 -O3 -Wall -Wextra -Werror native_tile_replay.cpp -o native-tile > build-tile.log 2>&1
cat > native-tile-host <<'WRAPPER'
#!/bin/bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")" && pwd)
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif "$root/native-tile"
WRAPPER
chmod u+x native-tile-host
"$python" -u -B native_tile_probe.py ./native-tile-host native-probe > native-probe.log 2>&1
"$python" -u -B tile_review.py "$2" generated --incumbent "$3" --wire-budget "${10}" --width 8 --column-proof proof/probes/column-v3-profile --row-proof proof/probes/probe-v5-profile --instance-services "$5" --write-ir > review.log 2>&1
sha256sum generated/* native-probe/* tests.log native-probe.log review.log > plan-output.sha256
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$9" native_reference.cpp -o native-reference > build-reference.log 2>&1
"$python" -u -B reuse_validate.py --tile-worker "$root/native-tile-host" generated/ir.json generated/selected.json "$6" "$7" "$8" replay "${sim[@]}" "$root/native-reference" > replay.log 2>&1
sha256sum generated/* replay/* native-probe/* tests.log native-probe.log review.log replay.log native-tile native-tile-host native-reference > output.sha256
