#!/usr/bin/env bash
set -euo pipefail
archive=$1
out=$2
checkpoint=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["models"]["qwen3"]["checkpoint"])' "$archive/suite-final.json")
bin=$archive/experiment/build/llm_cd_bench
python3 - "$archive/suite-final.json" "$bin" <<'PY'
import hashlib
import json
import sys

expected = json.load(open(sys.argv[1]))["models"]["qwen3"]["binary_sha256"]
with open(sys.argv[2], "rb") as f:
    actual = hashlib.sha256(f.read()).hexdigest()
if expected != actual:
    raise SystemExit("historical binary fingerprint mismatch")
print("binary_sha256=" + actual)
PY
unset LLM_LINK_CORRUPT LLM_LINK_DROP_RESPONSE LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED LLM_SSM_BLOCK_SCALES
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1
export LLM_ACCURATE_SILU=1 LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1
export LLM_FLOW_DIR="$out/qwen3-functional"
mkdir "$out/qwen3-functional"
cd "$out/qwen3-functional"
"$bin" "$checkpoint" .
for name in systemc_hidden.bin systemc_logits.bin; do
    cmp "$name" "$archive/run-qwen3/$name"
    sha256sum "$name"
done
