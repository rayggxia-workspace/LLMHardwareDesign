#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g=$2
d=$3
live=$4
out="$PWD/live-topology-$SLURM_JOB_ID"
mkdir -p "$out/DDR"
base="$d/geometry-110384/base.json"
link="$d/mother-ingress-sNMsK9/link-110415"
assets="$d/decode-program-110370"
python3 -B bind_gather_mother_topology.py "$link/mother.pm" "$link/request-link.json" "$base" "$assets/local.pm" "$out/native"
sha256sum --check --quiet "$live/run-111164/proof.sha256"
python3 -B - "$live" "$out" "$base" <<'PY'
import json,sys
from pathlib import Path
live,out,base=map(Path,sys.argv[1:])
topology=json.loads(base.read_bytes())['native_service_routes']['topology_id']
run=live/'run-111164'
s=(run/'live_token_gather.sv').read_text()
old="assert(mother_image[4][0+:32]==TOPOLOGY);"
assert s.count(old)==1
(out/'live_token_gather.sv').write_text(s.replace(old,f"assert(mother_image[4][0+:32]==32'd{topology});"))
(out/'test_native_projection_live.sv').write_bytes((run/'test_native_projection_live.sv').read_bytes())
runner=(live/'run_live_vocab_gather.sbatch').read_text()
head=runner[runner.index('root='):runner.index('out="$PWD/run-')]
tail=runner[runner.index('readarray -t params'):]
tail=tail.replace('"+GATHER_MOTHER=$link/mother.hex"','"+GATHER_MOTHER=$out/native/mother.hex"')
needle='"+GATHER_MOTHER=$out/native/mother.hex"'
assert tail.count(needle)==1
(out/'run.sh').write_text(head+tail)
PY
source "$out/run.sh"
