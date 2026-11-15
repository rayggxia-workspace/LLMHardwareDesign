#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-native
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
set -euo pipefail
name=$1
p=$(dirname "$(sacct -j 114252 -X -n -P -o WorkDir%500 | head -n1)")
odb=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["views"][sys.argv[2]+".odb"]["path"])' "$p/../overlay-111993/base.json" "$name")
test -f "$odb"
out=$(mktemp -d "$PWD/native-$name.XXXXXXXX")
cd "$out"
mkdir tmp
printf 'run=%s\narchive=%s\n' "$out" "$name"
sed 's/{metal7 metal8 metal9 metal10}/{metal7 metal8 metal9 metal10 via7 via8 via9}/g' "$p/export-pr271-metal.tcl" > export.tcl
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" env "AUDIT_ODB=$odb" "AUDIT_OUT=$out/native.tsv" openroad -no_init -exit "$out/export.tcl"
gzip native.tsv
sha256sum native.tsv.gz "$odb"
