from pathlib import Path
import hashlib,json
p=Path(__file__).parent
s=(p/'loader-distributed-parallel-reviewed.sv').read_text()
a="bb+({48'd0,f}*{32'd0,bst})+({53'd0,row_of(flat(word_index,lane))}*{32'd0,bst})+({61'd0,col_of(flat(word_index,lane))}*{32'd0,cst})"
b="bb+({48'd0,f}*{32'd0,bst})+({61'd0,col_of(flat(word_index,lane))}*{32'd0,cst})+({53'd0,row_of(flat(word_index,lane))}*{32'd0,bst})"
assert s.count(a)==1
c=s.replace(a,b)
o=p/'loader-rowlast.sv';o.write_text(c)
assert c.replace(b,a)==s
r={'source_sha':hashlib.sha256((p/'loader-distributed-parallel-reviewed.sv').read_bytes()).hexdigest(),'candidate_sha':hashlib.sha256(o.read_bytes()).hexdigest(),'proof':'Only reorders last two unsigned64 addends; modular2^64 associativity and commutativity. All operands explicitly64 and no intermediate truncation except natural64 arithmetic. Whole source inverse identity asserted. Two-state only.'}
(p/'loader-rowlast-binding.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
