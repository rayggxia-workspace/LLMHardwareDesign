#!/usr/bin/env bash
#SBATCH --job-name=zny-att1-tlm
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=03:40:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
mode=$1
weight=$2
root=/public/home/yuzelu/project-circuit
assets=$root/issue234-native-fixed-skip-request-H2gY5uiN
dependencies=$root/issue260-tlm-joint-9BiJdfEg
dram=$root/issue234-ddr-quiet-JDehtRNz/quiet/source
config=$root/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini
kv=$root/issue260-full-preflight-LUsXKLuZ/kv-106243/binding.json
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
program=$assets/request-runtime-archived
memory=$assets/request-memory-archived/ddr-initial.tsv
proof=74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef
kv_sha=78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e
sha256sum -c source.sha256
sha256sum "$program/proof.sha256" "$memory" "$kv" "$config" "$dram/libdramsim3.so" "$image" > "inputs-$SLURM_JOB_ID.sha256"
case $mode in
    decode) args=(--decode-kv-binding "$kv" --decode-kv-sha256 "$kv_sha") ;;
    prefill) args=(--prefill-tokens 2) ;;
    *) exit 2 ;;
esac
if [[ $weight == candidate ]]; then args+=(--ffn-rtl-weight-fetch); elif [[ $weight != baseline ]]; then exit 2; fi
out=run-$SLURM_JOB_ID
srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec \
    --cleanenv --bind /public/home/yuzelu "$image" bash -s -- \
    "$dependencies" "$dram" "$mode" "$program" "$memory" "$config" "$proof" "$out" "${args[@]}" <<'RUN'
set -euo pipefail
dependencies=$1 dram=$2 mode=$3 program=$4 memory=$5 config=$6 proof=$7 out=$8
shift 8
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/source:$dependencies/systemc_benchmark:$dependencies/block_local_native"
g++ --version > "$out.compiler.txt"
python3 --version > "$out.python.txt"
python3 -B -c 'from pathlib import Path; files = ["native_tlm_projection.py", "native_tlm_ffn.py", "run_native_tlm_request.py"]; [compile((Path("source") / f).read_bytes(), f, "exec") for f in files]'
g++ -std=c++17 -O3 -Wall -Wextra -Werror -shared -fPIC -isystem "$dram/src" -isystem "$dram/ext/headers" \
    fast_tlm_dram.cpp -L"$dram" -Wl,-rpath,"$dram" -ldramsim3 -o "$out.dram.so"
python3 -B fast_tlm_replay.py --archive "$PWD/source" --fast-ddr \
    "$program" "$memory" "$PWD/$out.dram.so" "$config" "$out" "$proof" \
    --pipeline-memory --dma-fabric-budget --kv-read-window 8 --sram-port-bits 512 "$@"
if [[ $mode == decode ]]; then
    python3 -B source/audit_native_decode_timing.py "$out" > "$out/timing-audit.json"
else
    python3 -B source/audit_prefill.py "$out" 2 > "$out/timing-audit.json"
fi
RUN
sha256sum source.sha256 "inputs-$SLURM_JOB_ID.sha256" "$out".{compiler.txt,python.txt,dram.so} \
    "$out"/{execution.json,page-timing.jsonl,timing-audit.json,ffn-weight-timing.jsonl,ffn-down.sha256.jsonl} > "$out/output.sha256"
sha256sum -c "$out/output.sha256"

