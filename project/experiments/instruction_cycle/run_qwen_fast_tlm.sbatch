#!/usr/bin/env bash
#SBATCH --job-name=zny-qwentlm
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=04:45:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
sha256sum -c source.sha256
root=/public/home/yuzelu/project-circuit
archive=$root/issue260-native-two-dma-sRx1azw1
asset=$root/issue234-native-fixed-skip-request-H2gY5uiN
dependencies=$root/issue260-tlm-joint-9BiJdfEg
dram=$root/issue234-ddr-quiet-JDehtRNz/quiet/source
config=$root/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini
kv=$root/issue260-full-preflight-LUsXKLuZ/kv-106243/binding.json
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
python=/public/home/yuzelu/Melodydt/runs/issue-265/reference-env-20261113-01/venv/bin/python
deployment=74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef
kv_sha=78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e
program=$asset/request-runtime-archived
memory=$asset/request-memory-archived/ddr-initial.tsv
reference=$archive/run-107361
cat > inputs.sha256 <<EOF
1bf5465dc4a4bbb8e4618502e1fe5a591d1c2c9fdc8b20cf84d5ea7d198e2a33  $archive/source.sha256
$deployment  $program/proof.sha256
$kv_sha  $kv
e55ce2d889261daccbf43335875be922fe813fe92dc0ae9ee28fd1f5b880d7b5  $memory
748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766  $config
363d38212c06ded6b012c609cf834d2176fb51acb41ec0fedca918768cfbe292  $dependencies/dram-106937.so
00ccc86ab97f9d25f84bdf6df22b4972e70b96ff56fc7dd39805b2280b14698f  $dram/libdramsim3.so
b750651e5fc871df216570cfa1687894f9242a16a26fb69bf1099a97f5080e4b  $dram/src/memory_system.h
601134bdb862045dd3002abe615284c5501deb36c064175fd84eb29bd2ac5837  $dependencies/systemc_benchmark/native_rtl_retirements.py
4b763d1dcb22840f70c11e81447591715369b8f37b7febdbdecc353949d870ef  $dependencies/systemc_benchmark/prepare_native_whole_request.py
7ed0eb23bbba07aabad7c257a4ba1f1e1dca09e8cca15768adfdf78e9e8b613b  $dependencies/block_local_native/native_program_runtime.py
49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image
EOF
sha256sum -c inputs.sha256
(cd "$archive" && sha256sum -c source.sha256)

srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec \
    --cleanenv --bind /public/home/yuzelu "$image" bash -s -- \
    "$python" "$archive" "$dependencies" "$dram" "$program" "$memory" "$config" "$kv" "$deployment" "$kv_sha" <<'RUN'
set -euo pipefail
python=$1 archive=$2 dependencies=$3 dram=$4 program=$5 memory=$6 config=$7 kv=$8 deployment=$9 kv_sha=${10}
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$dependencies/systemc_benchmark:$dependencies/block_local_native"
g++ --version > compiler-version.txt
"$python" --version > python-version.txt
g++ -std=c++17 -O3 -Wall -Wextra -Werror -shared -fPIC -isystem "$dram/src" -isystem "$dram/ext/headers" \
    fast_tlm_dram.cpp -L"$dram" -Wl,-rpath,"$dram" -ldramsim3 -o fast_tlm_dram.so > build.log 2>&1
args=(--decode-kv-binding "$kv" --decode-kv-sha256 "$kv_sha" --dma-fabric-budget)
start=${SECONDS}
"$python" -B fast_tlm_replay.py --archive "$archive" --pages 9 --fast-ddr \
    "$program" "$memory" "$PWD/fast_tlm_dram.so" "$config" fast-prefix "$deployment" "${args[@]}"
echo "$((SECONDS-start))" > fast-prefix.wall-seconds
start=${SECONDS}
"$python" -B fast_tlm_replay.py --archive "$archive" --pages 9 \
    "$program" "$memory" "$dependencies/dram-106937.so" "$config" baseline-prefix "$deployment" "${args[@]}"
echo "$((SECONDS-start))" > baseline-prefix.wall-seconds
head -n 9 "$archive/run-107361/page-timing.jsonl" > archived-prefix.jsonl
"$python" -B fast_tlm_replay.py --compare archived-prefix.jsonl baseline-prefix/page-timing.jsonl
"$python" -B fast_tlm_replay.py --compare archived-prefix.jsonl fast-prefix/page-timing.jsonl
sha256sum *-prefix.wall-seconds {baseline,fast}-prefix/page-timing.jsonl archived-prefix.jsonl > prefix.sha256
echo "MATCHED_9_PAGES, starting two-step decode"
start=${SECONDS}
"$python" -B fast_tlm_replay.py --archive "$archive" --fast-ddr \
    "$program" "$memory" "$PWD/fast_tlm_dram.so" "$config" decode "$deployment" "${args[@]}"
echo "$((SECONDS-start))" > decode.wall-seconds
"$python" -B "$archive/audit_native_decode_timing.py" decode > decode/timing-audit.json
RUN

cat > reference.sha256 <<EOF
df6c62434b009195035853e9577edbfe653824017af745bdeb81fceca111238d  $reference/execution.json
56b1238ca44f6796f4982e41d8f6674a7c6730c65b98c05afae23ba447ddc831  $reference/page-timing.jsonl
7dae55035c57c9c30545813a0495c7446df51d7f51c9389c750396c438fb9c92  $reference/timing-audit.json
EOF
sha256sum -c reference.sha256
for file in execution.json page-timing.jsonl timing-audit.json; do
    python3 -B fast_tlm_replay.py --compare "$reference/$file" "decode/$file"
done
sha256sum source.sha256 inputs.sha256 reference.sha256 prefix.sha256 fast_tlm_dram.so \
    compiler-version.txt python-version.txt decode.wall-seconds decode/{execution.json,page-timing.jsonl,timing-audit.json} > output.sha256
sha256sum -c output.sha256
