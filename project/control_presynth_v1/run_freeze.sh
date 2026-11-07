#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
profile=${PROFILE:?five/U,F,C,P,J or recovery/U,F,C,J}
out=${1:?new result directory}
mkdir -p "$out";out=$(cd "$out" && pwd)
python3 -B "$here/package.py" --profile "$profile" --stage "${NATIVE_STAGE:?}" --bank "${SRAM_BANK:?}" --platform "${PLATFORM:?}" --out "$out/package" > "$out/build.json"
python3 -B "$here/validate.py" --package "$out/package" --out "$out/checks" --verilator "${VERILATOR:?}" --yosys "${YOSYS:?}" --openroad "${OPENROAD:?}"
python3 -B "$here/test_package.py" --package "$out/package" --out "$out/guard-tests.json"
tar -czf "$out/control-handoff.tar.gz" -C "$out/package" .
find "$out" -type f -not -name result.sha256 -print0 | sort -z | xargs -0 sha256sum > "$out/result.sha256"
