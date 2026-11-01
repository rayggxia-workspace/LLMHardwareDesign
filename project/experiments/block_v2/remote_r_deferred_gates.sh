#!/bin/bash
#SBATCH --job-name=yzl-bv2-rfinalgates
#SBATCH --partition=c96
#SBATCH --cpus-per-task=96
#SBATCH --exclusive
#SBATCH --time=24:00:00
set -euo pipefail
root=$1
out=$2
test "$SLURM_CPUS_PER_TASK" -eq 96
case "$SLURM_JOB_NODELIST" in node1[3-8]|node2[56]) ;; *) exit 2;; esac
python3 - "$root" "$out" <<'PY'
import json,math,re,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);base=root.parent.parent
assert base.name=='issue143-seven-block-v2-20261030' and root.parent.name=='snapshots'
assert out.parent==base/'outputs' and out.name=='146'
accounting=subprocess.check_output(['sacct','-j','94507,94509','--noheader','--parsable2',
    '--format=JobIDRaw,State,ExitCode,MaxRSS'],universal_newlines=True)
rows={v.split('|')[0]:v.split('|')[1:] for v in accounting.splitlines()}
for job in ('94507','94509'):
    for name in (job,job+'.0'):
        assert rows[name][0]=='COMPLETED' and rows[name][1]=='0:0',(name,rows[name])
raw=base/'outputs/139/pnr/r'
producer=json.loads((raw/'receipt.json').read_text())
assert producer['passed']
flow=json.loads((raw/'native-flow.json').read_text())
assert flow['passed'] and flow['pipeline_completed'] and flow['top']=='block_v1_r'
native=json.loads((base/'outputs/141/diagnostic.json').read_text())
assert native['diagnostic_completed'] and native['mode']=='final-native'
assert native['native_drc_zero'] and native['native_drc_count']==0
assert not native['qualified'] and not native['native_leaf_accepted']
rss=rows['94507.0'][2];match=re.fullmatch(r'([0-9.]+)([KMGT])',rss);assert match,rss
peak=float(match[1])*1024**('KMGT'.index(match[2])+1)
forecast=max(192,32*math.ceil(peak/1024**3*1.3/32))
assert forecast<=384,('Actual native peak requires a revised memory plan',rss,forecast)
status={}
for seq in ('145','143'):
    f=base/'outputs'/seq/'function-r/receipt.json'
    if f.exists():
        receipt=json.loads(f.read_text());assert receipt['operation']=='function-compute'
        status[seq]=receipt['passed']
    else:status[seq]=None
selected=next((seq for seq in ('145','143') if status[seq] is True),None)
if selected is None:selected='143' if status['145'] is False else '145'
admission=dict(predecessors_ready=True,qualified=False,native_leaf_accepted=False,
    native_terminal_accounting=accounting,actual_native_peak_bytes=int(peak),formal_forecast_gib=forecast,
    selected_function_computation=selected,function_computation_status=status,
    scope='Scheduling readiness only. Existing strict seal/native/GDS/function/formal/physical/delivery gates remain unconditional; no native leaf qualification inferred.')
Path(str(out)+'.predecessor-admission.json').write_text(json.dumps(admission,indent=2)+'\n')
Path(str(out)+'.predecessor-arguments.txt').write_text(str(forecast)+' '+selected+'\n')
print(json.dumps(admission))
PY
read -r forecast function_seq < "$out.predecessor-arguments.txt"
base=$(dirname "$(dirname "$root")")
bash "$root/project/experiments/block_v2/remote_r_final_gates.sh" \
 "$root" "$base/outputs/139" "$out" "$base/outputs/141" "$base/outputs/138" "$forecast" \
 "$base/outputs/$function_seq/function-r" "$base/outputs/144/formal-r"
# Packaging invokes the existing accepted() gate again; it is unreachable when
# the queue or any required physical/function/formal/geometry dependency fails.
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" "$image" \
 /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$1/project/experiments/block_v2/bundle.py" --delivery "$2/deliver-r" --out "$2/bundle-r"' bash "$root" "$out"
