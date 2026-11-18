from pathlib import Path
import re,json
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-rcx-zero-normalization-v1';text=(p/'normalized.def').read_text();receipt=json.loads((p/'edit-receipt.json').read_text());section=re.search(r'\nNETS\s+\d+\s*;(.*?)\nEND NETS',text,re.S)[1];entries={m[1]:m[0] for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',section,re.M|re.S)};header=[]
for key in ('VERSION','DIVIDERCHAR','BUSBITCHARS','DESIGN','UNITS'):
 m=re.search(r'^'+key+r'\s+.*?;',text,re.M);assert m,key;header.append(m[0])
(p/'two-net-only.def').write_text('\n'.join(header)+'\nNETS 2 ;\n'+'\n'.join(entries[n] for n in receipt['target_nets'])+'\nEND NETS\nEND DESIGN\n')
old=p/'reextract';out=p/'reextract-mini';out.mkdir(exist_ok=False)
for n in ('geometry-all.tcl','def-material.py'):(out/n).write_bytes((old/n).read_bytes())
(out/'extract-consistency.tcl').write_text((old/'extract-consistency.tcl').read_text().replace('/normalized.def','/two-net-only.def'))
s=(p/'reextract.sbatch').read_text().replace('out=$r/audit/C-rcx-zero-normalization-v1/reextract','out=$r/audit/C-rcx-zero-normalization-v1/reextract-mini').replace('"$r/audit/C-rcx-zero-normalization-v1/normalized.def"','"$r/audit/C-rcx-zero-normalization-v1/normalized.def" "$r/audit/C-rcx-zero-normalization-v1/two-net-only.def"');(p/'reextract-mini.sbatch').write_text(s)
