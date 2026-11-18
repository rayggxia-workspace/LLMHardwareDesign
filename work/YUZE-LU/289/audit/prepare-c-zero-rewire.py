from pathlib import Path
import json
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-rcx-zero-normalization-v1';old=p/'reextract-mini';out=p/'reextract-rewire';out.mkdir(exist_ok=False)
for n in ('geometry-all.tcl','def-material.py'):(out/n).write_bytes((old/n).read_bytes())
receipt=json.loads((p/'edit-receipt.json').read_text());names=receipt['target_nets'];plan='set zero_nets {'+' '.join('{'+n+'}' for n in names)+'}\n'
plan+='''set zero_block [ord::get_db_block]
write_verilog original.v
foreach name $zero_nets {
 set n [$zero_block findNet $name]
 if {$n eq "NULL" || [$n getWire] eq "NULL"} {error "Missing exact normalized target net/wire: $name"}
 odb::dbWire_destroy [$n getWire]
}
'''
s=(old/'extract-consistency.tcl').read_text().replace('read_def -incremental ',plan+'read_def -incremental ',1)
s=s.replace('geometry_snapshot before-geometry.tsv','write_verilog imported.v\nexec cmp original.v imported.v\ngeometry_snapshot before-geometry.tsv',1)
check='''
exec python3 check-import.py
file mkdir import-check
file copy /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-rcx-zero-normalization-v1/normalized.def import-check/before.def
file copy before.def import-check/after.def
foreach name {layers.tsv vias.tsv} {file copy $name import-check/$name}
exec env C_CANON_BASE=[pwd]/import-check C_CANON_OUT=[pwd]/import-check/material klayout -b -r def-material.py > import-check/check.log 2>@1
exec python3 -c {import json; assert json.load(open("import-check/material/receipt.json"))["passed"]}
'''
s=s.replace('write_def before.def','write_def before.def'+check)
(out/'extract-consistency.tcl').write_text(s)
(out/'check-import.py').write_text('''from pathlib import Path
import re,json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-rcx-zero-normalization-v1');names=json.loads((p/'edit-receipt.json').read_text())['target_nets'];vals=[]
for path in (p/'normalized.def',Path('before.def')):
 t=path.read_text();sec=re.search(r'\\nNETS\\s+\\d+\\s*;(.*?)\\nEND NETS',t,re.S)[1];b={m[1]:' '.join(m[2].split()) for m in re.finditer(r'^\\s*-\\s+(\\S+)\\s+(.*?);\\s*$',sec,re.M|re.S)};vals.append({n:b[n] for n in names})
assert vals[0]==vals[1], 'Actual imported route instructions differ from proven normalized source'
Path('import-target-encoding.json').write_text(json.dumps(dict(passed=True,targets=names,exact_route_instruction_tokens=True),indent=2))
''')
s=(p/'reextract-mini.sbatch').read_text().replace('out=$r/audit/C-rcx-zero-normalization-v1/reextract-mini','out=$r/audit/C-rcx-zero-normalization-v1/reextract-rewire').replace('"$out/def-material.py"','"$out/def-material.py" "$out/check-import.py"');(p/'reextract-rewire.sbatch').write_text(s)
