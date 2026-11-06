#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
release="$PWD/release-eco-${SLURM_JOB_ID:?}"
mkdir "$release"
python3 - "$release" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

out = Path(sys.argv[1])
deck = Path("../../issue-188-ucf16/accepted-ucf16-01/C16/FreePDK45.lydrc")
full = {
    "P": Path("native-p-original-98190/native.lyrdb"),
    "C_final_BEOL": Path("native-beol-98421/native.lyrdb"),
    "U": Path("native-98147-U/eco-native.lyrdb"),
}
assert all(not ET.parse(str(p)).findall(".//items/item") for p in full.values())
old = Path("native-98146-C/native-full.log").read_text()
assert re.search(r'"space" in: FreePDK45\.lydrc:125\n\s+Edge pairs: 0 \(flat\)\s+0 \(hierarchical\)\n\s+Elapsed: [\d.]+s[^\n]*\n'
                 r'"output" in: FreePDK45\.lydrc:125\n\s+Edge pairs: 0 \(flat\)\s+0 \(hierarchical\)',old)
rule, = [row for row in deck.read_text().splitlines(keepends=True)
         if row.startswith("implant.space(45.nm, euclidian).output")]
assert "IMPLANT.4" in rule
complement = Path("native-complement-98198/drc-complement.lydrc")
assert deck.read_text().replace(rule,"\n") == complement.read_text()
c_gds = Path("native-98417-C/eco.gds")
old_violations = [i.findtext("category") for i in ET.parse(
    "native-complement-98198/native.lyrdb").findall(".//items/item")]
assert len(old_violations)==7 and set(old_violations)=={"'METAL3.1'","'METAL3.2'"}
delta = json.loads(Path("eco-98416-1/mask-delta.json").read_text())
assert delta["passed"] and delta["only_changed_mask"]=="M3" and delta["patch_count"]==4
old_raw = json.loads(Path("native-98146-C/well-equivalence.json").read_text())
new_raw = json.loads(Path("native-98417-C/well-equivalence.json").read_text())
assert old_raw["source_sha256"] == delta["before_sha256"]
assert new_raw["source_sha256"] == delta["after_sha256"]
assert old_raw["all_global_physical_masks_identical"] and new_raw["all_global_physical_masks_identical"]
assert new_raw["output_sha256"] == Path("native-beol-98421/input.sha256").read_text().splitlines()[2].split()[0]
expected = json.loads(Path("native-98146-C/well-equivalence.json").read_text())
actual = Path("native-complement-98198/input.sha256").read_text().splitlines()[2].split()[0]
assert expected["all_global_physical_masks_identical"] and expected["output_sha256"] == actual
assert "Total elapsed:" in Path("native-complement-98198/native-complement.log").read_text()
assert "Total elapsed:" in Path("native-p-original-98190/native.log").read_text()
geometry=json.loads(Path("eco-overlay-98425/klayout-receipt.json").read_text())
timing=json.loads(Path("split-valid-98154-0/timing-receipt.json").read_text())
assert geometry["passed"] and geometry["nets"]==297 and timing["passed_registered_coupon"]
for job in (98163,98094):
    assert len(list(Path(f"function-{job}").glob("run-*.log")))==3
    assert "PASS final ECO netlist, three initial conditions" in Path(f"function-{job}.log").read_text()
receipt = dict(passed=True, native_drc_markers={"P":0,"C":0,"U":0},
    native_full_deck_sha256=hashlib.sha256(deck.read_bytes()).hexdigest(),
    native_drc_job_ids={"P":[98190],"C":[98146,98198,98421,98422],"U":[98147]},
    c_canonical_sha256=new_raw["output_sha256"], c_canonical_path=str(c_gds),
    c_implant4_source="original deck completed IMPLANT.4 before Slurm time limit",
    c_complement_source="unchanged FEOL certified by four-rectangle M3-only delta; full BEOL, off-grid and antenna repeated on final GDS",
    native_reports={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in full.items()},
    geometry_job=98425,timing_jobs=[98423,98424],gate_sim_jobs=[98163,98094])
(out/"acceptance.json").write_text(json.dumps(receipt,indent=2)+"\n")
PY
cp split-valid-98154-0/{inputs.json,coupon.def,reservations.json,route.json,route-audit.json,timing-receipt.json} "$release/"
cp eco-overlay-98425/{gds-inputs.json,klayout-receipt.json,uncovered-via10.json,upper-only.gds} "$release/"
sha256sum eco-98154-0/{eco-routed.odb,eco-routed.def,eco-routed.v,candidate.lef,candidate.spef} \
  eco-98416-1/{eco-routed.odb,eco-routed.def,eco-routed.v,candidate.lef,candidate.spef} \
  eco-98057-2/{eco-routed.odb,eco-routed.def,eco-routed.v,candidate.lef,candidate.spef} \
  native-98162-P/eco-raw.gds native-98417-C/eco-raw.gds native-98140-U/eco-raw.gds > "$release/physical.sha256"
cmp eco-98416-1/eco-routed.v eco-98057-1/eco-routed.v
mkdir "$release"/{P,C,U}
cp native-p-original-98190/{native.lyrdb,native.log} "$release/P/"
cp native-98146-C/{native-full.log,well-equivalence.json} "$release/C/"
cp native-complement-98198/{drc-complement.lydrc,native-complement.log} "$release/C/"
cp native-complement-98198/native.lyrdb "$release/C/pre-repair.lyrdb"
cp native-complement-98198/input.sha256 "$release/C/pre-repair-input.sha256"
cp native-98147-U/{eco-native.lyrdb,native-full.log,well-equivalence.json} "$release/U/"
cp native-beol-98421/{native-beol.lydrc,native.log,native.lyrdb,input.sha256} "$release/C/"
cp eco-98416-1/{repairs.tsv,m3-screen.json,mask-delta.json,sta-1.log,extraction.log,restore.log} "$release/C/"
cp native-98417-C/well-equivalence.json "$release/C/well-equivalence-repaired.json"
cp timing-98423/timing-low.log timing-98424/timing-high.log "$release/"
cp ../../issue-188-ucf16/accepted-ucf16-01/C16/FreePDK45.lydrc "$release/"
cp function-98163/{run-*.log,input.sha256,results.sha256} "$release/P/"
cp function-98094/{run-*.log,input.sha256,results.sha256} "$release/U/"
(cd "$release"; find . -type f ! -name FILES.sha256 -print0 | sort -z | xargs -0 sha256sum > FILES.sha256; sha256sum -c FILES.sha256)
tar -C "$release" -czf "$release.tar.gz" .
sha256sum "$release.tar.gz"
