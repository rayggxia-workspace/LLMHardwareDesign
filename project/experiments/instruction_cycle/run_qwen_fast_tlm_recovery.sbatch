#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenaudit
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:06:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
failed=$(realpath "${1:?path to the sealed 110666 original run required}")
sha256sum -c source.sha256
root=/public/home/yuzelu/project-circuit
archive=$root/issue260-native-two-dma-sRx1azw1
reference=$archive/run-107361
dram=$root/issue234-ddr-quiet-JDehtRNz/quiet/source
config=$root/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini
kv=$root/issue260-full-preflight-LUsXKLuZ/kv-106243/binding.json
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
cat > inputs.sha256 <<EOF
1bf5465dc4a4bbb8e4618502e1fe5a591d1c2c9fdc8b20cf84d5ea7d198e2a33  $archive/source.sha256
d5d5f4883ddf51d4f79a2255bc0a2265937fc1ab1f539b0f8f599f9a80e43a74  $archive/audit_native_decode_timing.py
df6c62434b009195035853e9577edbfe653824017af745bdeb81fceca111238d  $reference/execution.json
56b1238ca44f6796f4982e41d8f6674a7c6730c65b98c05afae23ba447ddc831  $reference/page-timing.jsonl
7dae55035c57c9c30545813a0495c7446df51d7f51c9389c750396c438fb9c92  $reference/timing-audit.json
748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766  $config
78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e  $kv
00ccc86ab97f9d25f84bdf6df22b4972e70b96ff56fc7dd39805b2280b14698f  $dram/libdramsim3.so
1e74820e1cbe48b447e29fd9f98f55c54b4bd4f3fb493b0f2d8e1317c3cd8c1b  $failed/fast_tlm_dram.so
49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image
EOF
sha256sum -c inputs.sha256
(cd "$archive" && sha256sum -c source.sha256)
(cd "$failed" && sha256sum -c source.sha256 && sha256sum -c inputs.sha256 && sha256sum -c prefix.sha256)
srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec \
    --cleanenv --bind /public/home/yuzelu "$image" bash -s -- \
    "$failed" "$archive" "$reference" "$kv" "$config" <<'RUN'
set -euo pipefail
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
failed=$1 archive=$2 reference=$3 kv=$4 config=$5
python3 --version > python-version.txt
python3 -B recover_qwen_fast_tlm.py "$failed" "$kv" "$failed/fast_tlm_dram.so" "$config"
python3 -B "$archive/audit_native_decode_timing.py" recovered > recovered/timing-audit.json
for file in execution.json page-timing.jsonl timing-audit.json; do
    python3 -B fast_tlm_replay.py --compare "$reference/$file" "recovered/$file"
    echo "MATCHED $file"
done
for file in channel{0,1}/dramsim3{.json,.txt,epoch.json}; do
    cmp "$reference/$file" "recovered/$file"
    echo "MATCHED $file"
done
sha256sum source.sha256 inputs.sha256 python-version.txt close-smoke/stats.json \
    recovered/{execution.json,page-timing.jsonl,timing-audit.json} \
    recovered/channel{0,1}/dramsim3{.json,.txt,epoch.json} > output.sha256
sha256sum -c output.sha256
RUN
