#!/usr/bin/env bash
set -euo pipefail
mode=$1
work=$(realpath "$2")
original=/public/home/yuzelu/project-circuit/issue260-product-result-vocab-xlXs1bpB
exp=project/experiments/block_local_native
path=$exp/audit_algo1_vocabulary.py
printf '%s  %s\n' 6e03ee3f82811d9d537dc6d32e68fb7ef8f2fd4d5fea7e77eeda0ca25ff6bc50 "$original/source/$path" | sha256sum -c
cp "$original/source/$path" "$work/source/$path"
case $mode in
  bootstrap) exit 0 ;;
  0|1) ;;
  *) exit 2 ;;
esac
id=${work##*-}
cd "$work/typed-vocab-$id"
if [[ ! -f proof.sha256 ]]; then
    python3.11 -B "$work/source/$exp/audit_native_product_vocabulary.py" "$PWD" --step 126 --next-generation 2 > vocabulary-audit.json
    sha256sum ddr-audit.json vocabulary-audit.json tools.sha256 tool.txt generated/* replay-*.log DDR-*/{transactions.tsv,logits.hex,embedding.hex} > proof.sha256
fi
sha256sum -c proof.sha256 > verified-proof.log
cmp "DDR-$mode/logits.hex" "$original/typed-vocab-105394/generated/reference.hex"
grep -E '^HEAD_TIMING |^HEAD_ARGMAX |^NATIVE_VOCAB_INDEX_' "replay-$mode.log" > head-timing.log
sha256sum "$work/source/$path" head-timing.log proof.sha256 > head-timing.sha256
sha256sum -c head-timing.sha256
