#!/usr/bin/env bash
#SBATCH --job-name=mdt-280readpower
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
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
        bash "$bundle/run_bscc_t6_c639_read_power.sbatch" inside \
        "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$@"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/power-$3
family=$5
physical=$root/${6:?physical result directory}
case "$family" in
    shared) top=mc_dma_fabric_typed_p ;;
    phase) top=c639_dma_phase_ports ;;
    *) exit 2 ;;
esac
stage=$root/read-port-preflight/stage-38793408
(cd "$stage" && sha256sum --quiet -c results.sha256)
(cd "$physical" && sha256sum --quiet -c physical.sha256)
mkdir "$out"
export PYTHONPATH=$root/writer-power/frozen
python3 -B - "$physical" "$stage" "$out" "$family" "$top" "$4" <<'PY'
import json
from pathlib import Path
import re
import sys
from gate_power_300 import analyze

physical,stage,out=map(Path,sys.argv[1:4])
family,top,cores=sys.argv[4:]
key=Path("nangate45")/top/"base"
netlist=physical/"flow/results"/key
report=physical/"flow/logs"/key/"6_report.json"
drc=physical/"flow/reports"/key/"5_route_drc.rpt"
timing=json.loads(report.read_bytes())
setup=timing["finish__timing__setup__ws"]
hold=timing["finish__timing__hold__ws"]
ports={}
with (netlist/"6_final.v").open() as stream:
    for line in stream:
        if re.match(r"^\s*wire ",line):
            break
        match=re.match(r"^\s*(?:input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\w+);",line)
        if match:
            ports[match[3]]=int(match[1])-int(match[2])+1 if match[1] else 1
if not ports:
    raise ValueError("missing routed ports")
result={}
for path in sorted((stage/top).glob("*/ports.vcd")):
    activity_ports={}
    with path.open() as stream:
        for line in stream:
            fields=line.split()
            if fields[:1]==["$var"]:
                activity_ports[fields[4]]=int(fields[2])
            elif fields[:1]==["$enddefinitions"]:
                break
    if ports!=activity_ports:
        raise ValueError(f"routed power boundary differs: {path}")
    row=analyze(path,netlist,"dut",out/path.parent.name,10000,0,81920000,int(cores))
    result[path.parent.name]={"watts":row["power_w"],"energy_nj":row["energy_nj"],"annotated":row["annotated"]}
if len(result)!=6:
    raise ValueError("expected six qualified windows")
(out/"calibration.json").write_text(json.dumps({
    "family":family,"setup_ns":setup,"hold_ns":hold,"drc_report_empty":drc.is_file() and drc.stat().st_size==0,
    "note":"Phase wrapper includes shared read fabric. Do not add its total to the standalone shared fabric.",
    "windows":result,
},indent=2)+"\n")
PY
cd "$out"
sha256sum calibration.json */receipt.json > results.sha256
sha256sum -c results.sha256
