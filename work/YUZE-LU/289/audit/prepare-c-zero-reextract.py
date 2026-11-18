from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-rcx-zero-normalization-v1';out=p/'reextract';out.mkdir(exist_ok=False)
for n in ('geometry-all.tcl','def-material.py'):(out/n).write_bytes((r/'audit/C-final-v1'/n).read_bytes())
s=(r/'audit/C-final-v1/extract-consistency.tcl').read_text().replace('source geometry-all.tcl\ngeometry_snapshot before-geometry.tsv','source geometry-all.tcl\nset raw_geometry [geometry_snapshot original-geometry.tsv]\nread_def -incremental /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-rcx-zero-normalization-v1/normalized.def\nif {[geometry_snapshot imported-geometry.tsv] ne $raw_geometry} {error "Normalized DEF changed original interface geometry"}\ngeometry_snapshot before-geometry.tsv')
(out/'extract-consistency.tcl').write_text(s)
s=(r/'audit/C-final-v1/extract-consistency.sbatch').read_text();s=s.replace('run=$(realpath "$1")','run=$r/cu/runs/C-v20-native-clock4').replace('out=$r/audit/C-final-v1/rcx-$(basename "$run")','out=$r/audit/C-rcx-zero-normalization-v1/reextract').replace('mkdir "$out"','test -d "$out"').replace('cp "$r/audit/C-final-v1/"{extract-consistency.tcl,geometry-all.tcl,def-material.py} "$out/"','')
s=s.replace('"$out/"*.tcl "$out/def-material.py"','"$out/"*.tcl "$out/def-material.py" "$r/audit/C-rcx-zero-normalization-v1/normalized.def" "$r/audit/C-rcx-zero-normalization-v1/edit-receipt.json"')
(p/'reextract.sbatch').write_text(s)
