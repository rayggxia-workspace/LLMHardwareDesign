from pathlib import Path
import hashlib,json
p=Path(__file__).parent
s=(p/'loader-arithmetic-only.sv').read_text()
old="bb+({48'd0,f}+64'(row_of(flat(word_index,lane))))*bst+64'(col_of(flat(word_index,lane)))*cst"
new="bb+({48'd0,f}*{32'd0,bst})+({53'd0,row_of(flat(word_index,lane))}*{32'd0,bst})+({61'd0,col_of(flat(word_index,lane))}*{32'd0,cst})"
assert s.count(old)==1
(p/'loader-distributed.sv').write_text(s.replace(old,new))
r={'original_expression':old,'new_expression':new,'widths':{'f':16,'row':11,'col':3,'bst':32,'cst':32,'bb':64,'all_operands_in_new_expression':64},'proof':'In Z/(2^64), (f+row)*bst = f*bst+row*bst by distributivity. All operands are unsigned; original add is 64-bit due explicit concatenation/cast and expression context; all new add/mul operands explicitly 64-bit. Each intermediate multiplication is reduced modulo 2^64 in both expressions, which preserves the ring equality. No assumption about reachability or timing.', 'scope':'two-state bitvectors, all operand values; no four-state X equivalence','new_raw_sha256':hashlib.sha256((p/'loader-distributed.sv').read_bytes()).hexdigest()}
(p/'distributed-width-proof.json').write_text(json.dumps(r,indent=2)+'\n')
