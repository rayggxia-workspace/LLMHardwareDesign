#!/usr/bin/env bash
#SBATCH --job-name=yzl-ge-audit
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-5%6
#SBATCH --time=04:00:00
set -euo pipefail
root=$1
results=$2
destination=$3
shopt -s nullglob
candidates=("$results/"*-bands*)
index=${SLURM_ARRAY_TASK_ID:?}
(( index < ${#candidates[@]} )) || exit 0
candidate=${candidates[index]}
out="$destination/${candidate##*/}"
mkdir "$out"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r digest _ < <(sha256sum "$image")
test "$digest" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
srun --exclusive --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" \
 --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export PYTHONDONTWRITEBYTECODE=1
exp="$1/project/experiments/block_v2"; pnr=$2; out=$3; cpus=$4
if ! python3 "$exp/qualify.py" seal --source "$pnr" --out "$out/sealed"; then
 echo "No admitted native result. See original P&R receipt." > "$out/admission-failed.txt"
 exit 1
fi
odb=$(find "$out/sealed" -name 6_final.odb)
python3 "$exp/compact_occupancy.py" "$odb" "$out/occupancy.json"
status=0
python3 "$exp/qualify.py" physical --source "$out/sealed" --out "$out/physical" --cpus "$cpus" || status=1
printf "set_thread_count %s\nread_db {%s}\ndrt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 compact_whole_drc\n" "$cpus" "$odb" > native-drc.tcl
openroad -no_init -exit native-drc.tcl > native-drc.log 2>&1 || status=1
[[ -f native-whole-drc.rpt && ! -s native-whole-drc.rpt ]] || status=1
gds=$(find "$pnr/flow/results" -name 6_final.gds)
if [[ -z "$gds" ]]; then
 make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$pnr/config.mk" WORK_HOME="$pnr/flow" NUM_CORES="$cpus" do-gds > gds.log 2>&1
 gds=$(find "$pnr/flow/results" -name 6_final.gds)
fi
deck=/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc
klayout -b -rd in_gds="$gds" -rd report_file="$out/full-deck.lyrdb" -r "$deck" > full-deck.log 2>&1
sha256sum "$odb" "$gds" "$deck" "$out/full-deck.lyrdb" > "$out/drc-source.sha256"
python3 -c "import xml.etree.ElementTree as ET; n=len(ET.parse(\"full-deck.lyrdb\").findall(\".//items/item\")); print(n); assert n==0" > full-deck-count.txt || status=1
exit "$status"
' bash "$root" "$candidate/pnr" "$out" "$SLURM_CPUS_PER_TASK" > "$out/worker.log" 2>&1
