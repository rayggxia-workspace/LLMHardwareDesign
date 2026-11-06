#!/usr/bin/env bash
#SBATCH --job-name=yzl-ffndp-route
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
set -euo pipefail
repo=$1
out=$2
accepted=$3
overlay=$4
gap=${5:-128}
if [[ -e "$out" ]]; then echo "refusing to overwrite run: $out" >&2; exit 1; fi
mkdir -p "$out"
test_dir=$repo/project/experiments/qwen_ffn_dp
container=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
sim=("$container" exec --cleanenv --bind /public/home/yuzelu "$image")
expected=5f7de8fd080e159f044127f18673cb590137487068fdf6cdfad80a18cb411fab
printf '%s  %s\n' "$expected" "$accepted" | sha256sum -c -
member=$(tar tf "$accepted" | awk '/\/gates\/P-electrical\/block_p16.lef$/')
test -n "$member"
tar xOf "$accepted" "$member" > "$out/P16.lef"
tech="$overlay/research12.tech.lef"
tracks="$overlay/new_tracks.tcl"
python3 -B - "$test_dir/manifest.json" "$out/manifest.json" "$gap" <<'PY'
import json, sys
from pathlib import Path
base, output, gap = sys.argv[1:]
data = json.loads(Path(base).read_bytes())
data["base_id"] = f"p16-pair-payload-g{gap}-v0"
Path(output).write_text(json.dumps(data, indent=2) + "\n")
PY
python3 -B "$test_dir/compile_slice.py" "$out/manifest.json" "$out/mapping.json" --up-owner 1
python3 -B "$test_dir/route_coupon.py" "$out/mapping.json" "$out/P16.lef" "$tech" "$tracks" "$out/route" --gap "$gap"
cd "$out/route"
"${sim[@]}" openroad -version >tool-version.txt
set +e
"${sim[@]}" openroad -exit route.tcl >route.log 2>&1
status=$?
set -e
printf '%s\n' "$status" > openroad.exit
sha256sum coupon.def coupon.json payload.guide route.tcl route.log tool-version.txt openroad.exit > input-output.sha256
if [[ -f routed.def ]]; then
  sha256sum routed.def >> input-output.sha256
  python3 -B "$test_dir/route_feedback.py" coupon.json routed.def "$out/feedback.json" --cost-per-missing 1000
  python3 -B "$test_dir/compile_slice.py" "$out/manifest.json" "$out/remapped.json" --feedback "$out/feedback.json"
  python3 -B "$test_dir/images.py" "$out/remapped.json" "$out/remapped-images"
  sha256sum "$out/feedback.json" "$out/remapped.json" "$out/remapped-images/"*.hex >> input-output.sha256
fi
exit "$status"
