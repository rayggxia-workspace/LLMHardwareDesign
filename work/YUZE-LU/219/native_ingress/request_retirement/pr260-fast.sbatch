#!/usr/bin/env bash
set -euo pipefail
cd "$1"
code=$2
program=$3
memory=$4
binding=$5
mode=$6
width=$7
p=/public/home/yuzelu/project-circuit
tool="$p/issue250-u-n32-stored-link-20261112-01/tool.sh"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
out="$PWD/fast-$mode-$SLURM_JOB_ID"
read -r deployment _ < <(sha256sum "$program/proof.sha256")
read -r binding_hash _ < <(sha256sum "$binding")
case "$mode" in
    prefill) options=(--prefill-tokens 2); audit=(audit_prefill.py "$out" 2 --sram-port-bits "$width");;
    decode) options=(--decode-kv-binding "$binding" --decode-kv-sha256 "$binding_hash")
            audit=(audit_native_decode_timing.py "$out");;
    *) exit 2;;
esac
printf 'mode=%s width=%s deployment=%s kv_binding=%s\n' "$mode" "$width" "$deployment" "$binding_hash"
bash "$tool" env OPENBLAS_NUM_THREADS=1 "$py" -B "$code/run_native_tlm_request.py" \
    "$program" "$memory" "$p/issue260-tlm-joint-9BiJdfEg/dram-106937.so" \
    "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "$out" "$deployment" \
    "${options[@]}" --pipeline-memory --dma-fabric-budget --kv-read-window 8 --sram-port-bits "$width"
bash "$tool" "$py" -B "$code/${audit[0]}" "${audit[@]:1}" > "$out/timing-audit.json"
sha256sum "$out/"{execution.json,page-timing.jsonl,timing-audit.json}
cat "$out/timing-audit.json"
