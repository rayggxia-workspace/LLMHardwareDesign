#!/usr/bin/env bash
set -euo pipefail
script=$(cd "$(dirname "$0")" && pwd -P)
mkdir "${1:?Usage: bash smoke_test.sh NEW_OUTPUT_DIR}"
cd "$1"
mkdir tmp
export TMPDIR="$PWD/tmp" XDG_CACHE_HOME="$PWD/tmp" QT_QPA_PLATFORM=offscreen
cp "$script/base-manifest.example.json" manifest.json
klayout -b -r "$script/smoke_fixture.py" -rd mode=create
bash "$script/run.sh" manifest.json result
klayout -b -r "$script/smoke_fixture.py" -rd mode=check
