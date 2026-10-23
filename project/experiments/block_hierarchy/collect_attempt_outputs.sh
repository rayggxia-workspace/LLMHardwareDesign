#!/usr/bin/env bash
# Compute-node failure/success artifact hashing. The caller retains its own rc.
set -euo pipefail
{
  find "$LLHD_ATTEMPT" -maxdepth 1 -type f \
    \( -name '*.json' -o -name '*.tsv' -o -name '*.rpt' -o -name '*.log' -o -name '*.txt' -o -name '*.odb' \) -print0
  for folder in "$LLHD_ATTEMPT/flow/results" "$LLHD_ATTEMPT/macro-view"; do
    if test -d "$folder"; then find "$folder" -type f -print0; fi
  done
} | sort -z | xargs -0 -r sha256sum > result-files.sha256
