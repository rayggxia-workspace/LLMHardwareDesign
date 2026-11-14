#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenbw
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=03:40:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
case ${1:?archived case ID required} in
    107947) name=issue260-native-kv-window-jL6neTvA; width=128; mode=decode ;;
    108284) name=issue260-native-sram512-SMbOWTw6; width=512; mode=decode ;;
    108359) name=issue260-native-sram512-full-zrXP7jjS; width=512; mode=prefill ;;
    110382) name=issue260-sram-pipeline-qk3uTFl1; width=512; mode=decode ;;
    110383) name=issue260-sram-pipeline-qk3uTFl1; width=512; mode=prefill ;;
    *) echo "unsupported reference case: $1" >&2; exit 2 ;;
esac
job=$1
sha256sum -c source.sha256
sha256sum -c "reference-$job.sha256"
root=/public/home/yuzelu/project-circuit
archive=$root/$name
reference=$archive/run-$job
asset=$root/issue234-native-fixed-skip-request-H2gY5uiN
dependencies=$root/issue260-tlm-joint-9BiJdfEg
dram=$root/issue234-ddr-quiet-JDehtRNz/quiet/source
config=$root/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini
kv=$root/issue260-full-preflight-LUsXKLuZ/kv-106243/binding.json
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
deployment=74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef
kv_sha=78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e
program=$asset/request-runtime-archived
memory=$asset/request-memory-archived/ddr-initial.tsv
cat > inputs.sha256 <<EOF
$deployment  $program/proof.sha256
$kv_sha  $kv
e55ce2d889261daccbf43335875be922fe813fe92dc0ae9ee28fd1f5b880d7b5  $memory
748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766  $config
00ccc86ab97f9d25f84bdf6df22b4972e70b96ff56fc7dd39805b2280b14698f  $dram/libdramsim3.so
b750651e5fc871df216570cfa1687894f9242a16a26fb69bf1099a97f5080e4b  $dram/src/memory_system.h
601134bdb862045dd3002abe615284c5501deb36c064175fd84eb29bd2ac5837  $dependencies/systemc_benchmark/native_rtl_retirements.py
4b763d1dcb22840f70c11e81447591715369b8f37b7febdbdecc353949d870ef  $dependencies/systemc_benchmark/prepare_native_whole_request.py
7ed0eb23bbba07aabad7c257a4ba1f1e1dca09e8cca15768adfdf78e9e8b613b  $dependencies/block_local_native/native_program_runtime.py
49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image
EOF
sha256sum -c inputs.sha256
(cd "$archive" && sha256sum -c source.sha256)
if [[ $mode == decode ]]; then
    args=(--decode-kv-binding "$kv" --decode-kv-sha256 "$kv_sha")
else
    args=(--prefill-tokens 2)
fi
args+=(--dma-fabric-budget --kv-read-window 8)
if [[ $width == 512 ]]; then
    args+=(--sram-port-bits "$width")
fi
if [[ $job == 110382 || $job == 110383 ]]; then
    args+=(--pipeline-memory)
fi
printf 'Running reference %s: %s, %s-bit SRAM, %s\n' "$job" "$mode" "$width" "${args[*]}"
srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec \
    --cleanenv --bind /public/home/yuzelu "$image" bash -s -- \
    "$archive" "$dependencies" "$dram" "$mode" "$program" "$memory" "$config" "$deployment" "${args[@]}" <<'RUN'
set -euo pipefail
archive=$1 dependencies=$2 dram=$3 mode=$4 program=$5 memory=$6 config=$7 deployment=$8
shift 8
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$archive:$dependencies/systemc_benchmark:$dependencies/block_local_native"
# Put the sealed configuration before the shared fallback modules. Import it
# through fast_tlm_replay, which replaces only the DDR device/clock path.
g++ --version > compiler-version.txt
python3 --version > python-version.txt
g++ -std=c++17 -O3 -Wall -Wextra -Werror -shared -fPIC -isystem "$dram/src" -isystem "$dram/ext/headers" \
    fast_tlm_dram.cpp -L"$dram" -Wl,-rpath,"$dram" -ldramsim3 -o fast_tlm_dram.so > build.log 2>&1
start=$SECONDS
python3 -B fast_tlm_replay.py --archive "$archive" --fast-ddr \
    "$program" "$memory" "$PWD/fast_tlm_dram.so" "$config" candidate "$deployment" "$@"
echo "$((SECONDS-start))" > candidate.wall-seconds
if [[ $mode == decode ]]; then
    python3 -B "$archive/audit_native_decode_timing.py" candidate > candidate/timing-audit.json
else
    python3 -B "$archive/audit_prefill.py" candidate 2 > candidate/timing-audit.json
fi
RUN
python3 -B compare_qwen_sram_sweep.py "$mode" "$reference" candidate > comparison.json
sha256sum source.sha256 "reference-$job.sha256" inputs.sha256 compiler-version.txt python-version.txt \
    fast_tlm_dram.so candidate.wall-seconds comparison.json candidate/{execution.json,page-timing.jsonl,timing-audit.json} \
    > output.sha256
sha256sum -c output.sha256
