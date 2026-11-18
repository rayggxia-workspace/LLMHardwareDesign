#!/usr/bin/env bash
#SBATCH --job-name=mdt-280control-activity
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum --quiet -c inputs.sha256
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_c639_control_activity.sbatch" inside "$bundle" "$SLURM_JOB_ID"
fi
cd "$2"
root=$(dirname "$PWD")
out=activity-$3
raw=$root/m-product/wide-38792112/replay-38792112
fst_scope=$root/writer-power/frozen/fst_scope_vcd
(cd "$raw" && sha256sum --quiet -c wide-results.sha256)
mkdir "$out"
python3 -B - "$raw" "$out" "$fst_scope" <<'PY'
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

raw,out,converter=map(Path,sys.argv[1:])
root="TOP/test_native_decode638_product_replay/controller"
scopes={root:"product_controller_boundary",
        root+"/cohort/mother/mother/core":"mother_core",
        root+"/cohort/mother/transport":"mother_transport_boundary"}
for index in range(4):
    node=f"{root}/cohort/local_target[{index}]"
    scopes[node+"/local_controller"]=f"local_controller_{index}"
    scopes[node+"/dispatch"]=f"local_dispatch_{index}"
manifest={}
for mode in range(2):
    for stage in ("gate-up","down","writer-active"):
        sample=raw/f"DDR-{mode}"/f"ffn-{stage}.fst"
        name=f"mode-{mode}-{stage}"
        vcd=out/f"{name}.tmp.vcd"
        subprocess.run([str(converter),str(sample),str(vcd),root],check=True,stdout=subprocess.DEVNULL)
        pins=defaultdict(list)
        levels={}
        flips=defaultdict(int)
        stack=[]
        with vcd.open() as stream:
            for line in stream:
                f=line.split()
                if f[:1]==["$scope"]:
                    stack.append(f[2])
                elif f[:1]==["$upscope"]:
                    stack.pop()
                elif f[:1]==["$var"]:
                    scope="/".join(stack)
                    if scope in scopes and re.search(r"(valid|ready|enable|retir|grant|owner)",f[4]):
                        pins[f[3]].append((scope,f[4],int(f[2])))
                elif f[:1]==["$enddefinitions"]:
                    break
            for line in stream:
                f=line.split()
                if not f:
                    continue
                if f[0][0] in "bB" and len(f)==2:
                    value,ident=f[0][1:],f[1]
                elif f[0][0] in "01xz":
                    value,ident=f[0][0],f[0][1:]
                else:
                    continue
                if ident not in pins:
                    continue
                level=int(value,2)
                if ident in levels:
                    flips[ident]+=bin(level^levels[ident]).count("1")
                levels[ident]=level
        result=defaultdict(dict)
        for ident,signals in pins.items():
            for scope,pin,width in signals:
                if ident not in levels:
                    raise ValueError(f"missing control waveform {name}/{scope}/{pin}")
                result[scopes[scope]][pin]={"width":width,"vcd_id":ident,"bit_flips":flips[ident]}
        if set(result)!=set(scopes.values()):
            raise ValueError(f"missing requested control scope in {name}")
        manifest[name]={"source":str(sample),"fst_sha256":sha256(sample.read_bytes()).hexdigest(),
                        "scopes":result}
        vcd.unlink()
(out/"control-activity.json").write_text(json.dumps({
    "scopes":{role:path for path,role in scopes.items()},"windows":manifest,
    "note":"Logical waveform boundaries. PM arrays, U datapath and typed read DMA are separate; "
           "shared VCD aliases are retained for physical no-double-count mapping.",
},indent=2)+"\n")
PY
cd "$out"
sha256sum control-activity.json > results.sha256
sha256sum -c results.sha256
