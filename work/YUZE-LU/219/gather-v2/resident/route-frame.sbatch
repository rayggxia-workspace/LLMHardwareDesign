#!/usr/bin/env bash
set -euo pipefail
cd "$1"
stage="$2"; g="$3"
root=/public/home/yuzelu/project-circuit
old="$root/issue250-u-n32-stored-link-20261112-01"
out="$PWD/frame-route-$SLURM_JOB_ID"
mkdir "$out"
sha256sum -c "$stage/artifacts.sha256"
bash "$old/tool.sh" env GATHER_PLACE="$stage" GATHER_ROUTE="$out" openroad -no_init -exit route-frame-gather.tcl
bash "$old/tool.sh" env NATIVE_DMA_GRT="$out/u-grt.odb" NATIVE_DMA_GUIDES="$out/route.guide" \
  NATIVE_DMA_LANDINGS="$out/dma-landings.tsv" NATIVE_DMA_OUTPUT="$out" \
  openroad -no_init -exit "$g/route-dma-m10-detail.tcl"
test "$(wc -l < "$out/routes.tsv")" -eq 651
test ! -s "$out/drc.rpt"
mv "$out/dma-detail.odb" "$out/u-dma-access.odb"
sha256sum "$out/"{route.guide,routes.tsv,drc.rpt,u-dma-access.odb} > "$out/artifacts.sha256"
