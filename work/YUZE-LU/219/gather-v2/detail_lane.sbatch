#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"
src="$PWD/stage-$3"
sha256sum --check "$src/global.sha256"
sha256sum --check "$src/landing-files.sha256"
out="$PWD/detail-$SLURM_JOB_ID"
mkdir "$out"
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" env NATIVE_DMA_GRT="$src/dma-grt.odb" NATIVE_DMA_GUIDES="$src/route.guide" \
  NATIVE_DMA_LANDINGS="$src/landings.tsv" NATIVE_DMA_OUTPUT="$out" \
  openroad -no_init -exit "$g/route-dma-m10-detail.tcl"
test ! -s "$out/drc.rpt"
test "$(wc -l < "$out/routes.tsv")" -eq 5029
sha256sum "$out/routes.tsv" "$out/dma-detail.odb" "$out/drc.rpt" > "$out/results.sha256"
