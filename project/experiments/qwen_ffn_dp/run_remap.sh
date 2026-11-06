#!/usr/bin/env bash
#SBATCH --job-name=yzl-ffndp
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
set -euo pipefail
repo=$1
native=$2
route=$3
selection=$4
out=$5
case "$selection" in remapped|metal-remapped|pin-bound-remapped) ;; *) exit 2 ;; esac
mkdir "$out"
test_dir=$repo/project/experiments/qwen_ffn_dp
container=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
sim=("$container" exec --cleanenv --bind /public/home/yuzelu "$image")
mapping="$route/$selection.json"
images="$route/$selection-images"
owner=$("${sim[@]}" python3 -B -c 'import json, sys; print(json.load(open(sys.argv[1]))["plan"]["up_owner"])' "$mapping")
test "$owner" = 0
test "$owner" != "$("${sim[@]}" python3 -B -c 'import json, sys; print(json.load(open(sys.argv[1]))["plan"]["up_owner"])' "$route/mapping.json")"
sha256sum "$mapping" "$images/"*.hex >"$out/remap-input.sha256"
pids=()
for i in 0 1 2 3 4 5; do
  (
    "${sim[@]}" "$native/obj/Vtb_ffn" "+vectors=$native/$i" "+images=$images" "+stall=$((i*2))" >"$out/rtl-$i.log" 2>&1
    "${sim[@]}" "$native/systemc-trial" "$native/$i" "$images" "$((i*2))" >"$out/sc-$i.log" 2>&1
    "${sim[@]}" python3 -B "$test_dir/compare_traces.py" "$out/rtl-$i.log" "$out/sc-$i.log" "$owner" >"$out/compare-$i.log"
  ) &
  pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
((status==0))
(cd "$out"; sha256sum ./*.log remap-input.sha256 > receipt.sha256)
