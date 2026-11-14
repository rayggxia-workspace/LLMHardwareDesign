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
sha256sum "$out/staged-ports.tsv"
