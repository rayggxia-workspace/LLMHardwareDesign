#!/usr/bin/env bash
set -euo pipefail
cd "$1"
archive=$2
request=$3
case_dir="$PWD/live-qkv-$SLURM_JOB_ID"
mkdir -p "$case_dir/generated" "$PWD/tmp"
cp "$archive"/replay-104175/generated/* "$case_dir/generated/"
python3 -B bind_live_qkv_kvr1.py "$archive/replay-104175/generated" "$request" "$case_dir/generated"
python3 -B - "$archive" "$case_dir" <<'PY'
from pathlib import Path
import sys

archive,out=map(Path,sys.argv[1:])
runner=(archive/'source/project/experiments/block_local_native/run_decode638_q_tile_replay.sh').read_text()
start=runner.index('source /OpenROAD-flow-scripts/env.sh')
end=runner.index('if [[ "$scope" == page-barrier ]]; then')
head=runner[start:runner.index('case "$scope" in')]
tail=runner[end:]
head=head.replace('case_dir="$run/replay-$SLURM_JOB_ID"','case_dir="$out"')
pre='''tiles=20
c_defs=-DFFN_DDR_WRITE
provider_sources=(-I"$EXP" "$N"/{ddr_s128_load_scope,s128_ddr_range_load,s32_add_scope,s128_rope_scope,s128_kv_store_scope}.sv)
runtime=("+ADDITIONAL_WEIGHTS=$g/assets.txt" "+QKV_STORE_PLAN=$g/kv-stores.tsv")
layout=$root/issue234-native-rope-ddr-assets-20261112-01/run-103592/layout.json
'''
(out/'run.sh').write_text('set -euo pipefail\n'+head+pre+tail)
PY
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
bash "$tool" bash -c 'out=$1; shift; source "$out/run.sh"' _ "$case_dir" "$archive" unused page-barrier
