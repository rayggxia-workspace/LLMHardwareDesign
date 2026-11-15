#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mmap
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=01:00:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=${SLURM_SUBMIT_DIR:?}
job=$SLURM_JOB_ID
cluster=$base/project-circuit
runs=$base/Melodydt/runs/issue-280
frozen=$runs/c639-g32-gate-01/c639-g32-116937
old=$cluster/issue250-m-physical-20261111-60
proof=$runs/c639-m-contract-02/contract-116953
exp=project/experiments/w8a16_weight
rtl=project/rtl/w8a16_v1
vlt=$base/opt/eda/verilator-5.042/bin/verilator
image=$base/opt/eda/containers/orfs-current-repacked.sif
singularity=/public/software/singularity-ce-4.3.4/bin/singularity
cd "$bundle"
sha256sum -c bundle.sha256

if [[ ${1:-} == route ]]; then
    map=$bundle/map-${2:?mapping job ID required}
    (cd "$map" && sha256sum -c mapping-results.sha256)
    dest=$bundle/route-$job
    mkdir "$dest"
    work=$map
    stage_tmp=$dest/tmp
else
    work=$bundle/map-$job
    stage_tmp=$work/tmp
    mkdir "$work"
    sha256sum --quiet -c "$proof/contract-results.sha256"
    (cd "$frozen" && sha256sum --quiet -c gate-results.sha256)
    (cd "$old" && sha256sum --quiet -c source.sha256)
    cp -a "$old/source" "$work/source"
    cp "$frozen/source/$exp/m_native_leaf_s32.sv.in" "$work/source/$exp/m_native_leaf_s32.sv.in"
    for name in m_native_leaf_s32 m_native_s32 weight_records m_group_s32 projection_context_s32 scale_group_s32; do
        cp "$frozen/source/$rtl/$name.sv" "$work/source/$rtl/$name.sv"
    done
    python3 -B - "$work/source" "$frozen/source" "$proof/sources.json" <<'PY'
import hashlib
import json
from pathlib import Path
import runpy
import sys

source, frozen, proof = map(Path, sys.argv[1:])
exp = source / 'project/experiments/w8a16_weight'
rtl = Path('project/rtl/w8a16_v1')
leaf = source / rtl / 'm_native_leaf_s32.sv'
template = exp / 'm_native_leaf_s32.sv.in'
generate = runpy.run_path(str(exp / 'generate_leaf.py'))['generate']
exact = leaf.read_text()
suffix = 'endmodule\n'
probe, = [text for text in exact.split('`ifndef SYNTHESIS') if text.endswith(suffix)]
assert probe.endswith('`endif\n' + suffix) and exact.count('`ifndef SYNTHESIS') == 1
assert generate() == exact[:exact.index('`ifndef SYNTHESIS')] + suffix
old_template = template.read_text()
assert old_template.endswith(suffix)
template.write_text(old_template[:-len(suffix)] + '`ifndef SYNTHESIS' + probe)
assert generate() == exact
driver = exp / 'leaf.cpp'
text = driver.read_text()
anchor = 'int main(int argc,char**argv){try{'
assert text.count(anchor) == 1 and 'Verilated::commandArgs' not in text
driver.write_text(text.replace(anchor, anchor + 'Verilated::commandArgs(argc,argv);'))
for module, info in json.loads(proof.read_text())['rtl'].items():
    file = rtl / (module + '.sv')
    assert hashlib.sha256((source / file).read_bytes()).hexdigest() == info['c639']
    assert (source / file).read_bytes() == (frozen / file).read_bytes()
PY
    mkdir "$work/vectors"
    vectors=$cluster/issue250-weight-20261111-114/vectors
    printf '%s  %s\n' \
      ee0b3e77a52886f5d4461adb100f8ee4cb4a02641fcb62b59651942732dbe5aa "$vectors/leaf.txt" \
      5abf48c82a4ad5efa4f4473bf64f5604519f1059546a7067fd39c2a684cd27d1 "$vectors/records.txt" > "$work/vector-source.sha256"
    sha256sum -c "$work/vector-source.sha256"
    cp "$vectors/"{leaf,records}.txt "$work/vectors/"
    (cd "$work" && sha256sum source/"$rtl"/{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32}.sv \
      source/"$exp"/{m_native_leaf_s32.sv.in,generate_leaf.py,leaf_check.py,leaf.cpp,m_map.py,m_route.py} vectors/*.txt > inputs.sha256)
fi

mkdir "$stage_tmp"
container() {
    local cores=$1
    shift
    srun --exact -n1 -c "$cores" --cpu-bind=cores "$singularity" exec --cleanenv --bind "$base" --pwd "$work/source" \
      --env "TMPDIR=$stage_tmp,XDG_CACHE_HOME=$stage_tmp,OMP_NUM_THREADS=$cores,OPENBLAS_NUM_THREADS=1,PYTHONDONTWRITEBYTECODE=1" "$image" \
      bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec "$@"' bash "$@"
}
if [[ ${1:-} == route ]]; then
    container 12 python3 -B "$work/source/$exp/m_route.py" --mapping "$work/mapping/m_native_leaf_s32" \
      --out "$dest/native" --side 1390 --bands 2 --margin 14 --density 0.55 --pin-profile edge \
      --setup-margin 0.100 --hold-margin 0.03 --grt-hold-buffer-percent 2 > "$dest/route.log" 2>&1
    test -f "$dest/native/receipt.json"
    final=$dest/native/flow/results/nangate45/bv1_m_native_leaf_s32/base
    sha256sum "$dest/native/"{receipt.json,native-flow.json} "$final"/6_final.{v,odb,spef,sdc} > "$dest/route-results.sha256"
    sha256sum -c "$dest/route-results.sha256"
    printf '%s\n' 'C639_EXACT_M_ROUTE_FLOW_PASS'
    exit 0
fi

for start in 25011 25014; do
    pids=()
    for seed in $(seq "$start" "$((start + 2))"); do
        container 4 python3 -B "$work/source/$exp/leaf_check.py" --source "$work/source" \
            --out "$work/leaf-seed-$seed" --vectors "$work/vectors" --seed "$seed" --jobs 4 --verilator "$vlt" \
            > "$work/leaf-seed-$seed.log" 2>&1 &
        pids+=("$!")
    done
    failed=0
    for pid in "${pids[@]}"; do if ! wait "$pid"; then failed=1; fi; done
    if ((failed)); then exit 1; fi
done
printf '%s\n' 'C639_EXACT_M_LEAF_18_RUNS_PASS'
container 12 python3 -B "$work/source/$exp/m_map.py" --rtl-run "$work" \
    --out "$work/mapping/m_native_leaf_s32" --leaf --flat-before-abc > "$work/mapping.log" 2>&1
cat "$work/mapping.log"
cd "$work"
sha256sum inputs.sha256 vector-source.sha256 leaf-seed-*/{result.json,initial-*.log} \
    mapping/m_native_leaf_s32/{receipt.json,mapped.json,mapped.v} > mapping-results.sha256
sha256sum -c mapping-results.sha256
printf '%s\n' 'C639_EXACT_M_MAPPING_PASS'
