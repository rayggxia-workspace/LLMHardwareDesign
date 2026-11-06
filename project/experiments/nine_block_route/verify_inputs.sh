#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
sha256sum -c input-r5.sha256
for kind in P J; do
  case "$kind" in
    P) archive=accepted-p16.tar.gz ;;
    J) archive=accepted-j16.tar.gz ;;
  esac
  folder="../issue-187-p16-j16/144-release-preflight/$kind"
  (cd "$folder"; sha256sum -c release.sha256)
  member="$(tar tf "$folder/$archive" | awk '/\/gates\/[PJ]-electrical\/block_[pj]16.lef$/')"
  test -n "$member"
  tar xOf "$folder/$archive" "$member" | cmp "$kind.lef"
done
folder="../issue-188-ucf16/accepted-ucf16-01"
for kind in U C F; do
  member="$(tar tf "$folder/${kind}16.tar.gz" | awk '/(^|\/)physical-abstract.lef$/')"
  test -n "$member"
  tar xOf "$folder/${kind}16.tar.gz" "$member" | cmp "$kind.lef"
done
echo PASS
