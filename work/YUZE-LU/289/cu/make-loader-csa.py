from pathlib import Path
import hashlib,json
p=Path(__file__).parent
s=(p/'loader-distributed-parallel.sv').read_text()
old="   else addr=bb+({48'd0,f}*{32'd0,bst})+({53'd0,row_of(flat(word_index,lane))}*{32'd0,bst})+({61'd0,col_of(flat(word_index,lane))}*{32'd0,cst});"
new="""   else begin
    base_term=bb+({48'd0,f}*{32'd0,bst});
    row_term={53'd0,row_of(flat(word_index,lane))}*{32'd0,bst};
    col_term={61'd0,col_of(flat(word_index,lane))}*{32'd0,cst};
    addr=(base_term^row_term^col_term)+(((base_term&row_term)|(base_term&col_term)|(row_term&col_term))<<1);
   end"""
assert s.count(old)==1
head=' function automatic [63:0] addr(input [8:0] word_index,input [1:0] lane);'
assert s.count(head)==1
s=s.replace(head,head+'\n  reg [63:0] base_term,row_term,col_term;').replace(old,new)
(p/'loader-csa.sv').write_text(s)
(p/'csa-transform.json').write_text(json.dumps({'before_raw_sha256':hashlib.sha256((p/'loader-distributed-parallel.sv').read_bytes()).hexdigest(),'after_raw_sha256':hashlib.sha256((p/'loader-csa.sv').read_bytes()).hexdigest(),'old':old,'new':new,'temporary_widths':64,'scope':'Stable two-state modulo 2^64 identity; no state or cycle changes'},indent=2)+'\n')
